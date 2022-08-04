import common
import lcd_driver
import timers

message_type_map = { #dizionario che definisce i tipi di messaggio possibili con placeholder %s
    "password":"Enter password: %s",
    "greet": "NOCTUA",
    "wrong-password":"WRONG PASSWORD!",
    "alarmed":"     ALARM          ENABLED",
    "not-alarmed":"     ALARM         DISABLED",
    "default":"ALARM %sNr. DEVICES:%s",
    "device-connected":"%sCONNECTED",
    "device-disconnected":"%sDISCONNECTED",
    "in-room":"IN ROOM         %s", #dettaglio sulla stanza in cui è successo quacosa
    "movement-detected":"MOVEMENT        DETECTED", #evento movimento
    "door-open-detected":"DOOR OPENED", #evento porta aperta
    "alarm-movement":"MOVEMENT IN     %s", #allarme innescato causa movimento
    "alarm-door":"DOOR OPEN IN    %s" #allarme innescato causa porta aperta
}
default_message=False #Abilita o disabilita il messaggio di default


def get_next_message():
    """
    PRE: La funzione deve essere chiamata quando si possiede il LOCK associato alla variabile condition DISPLAY_QUEUE_UPDATED.
    Restituisce il prossimo messaggio da mostrare e la sua priorità prelevandolo dalla coda di priorità 
    common.STATE['display-queue']. Se non c'è nessun messaggio nella coda restituisce (None,None)
    """
    #print("[LCD] Cerco un messaggio nella coda")
    display_queue=common.STATE['display-queue']
    next_message=None
    next_message_priority=None
    for (priority,queue) in display_queue.items():
        #print("[LCD] Controllo priority ",priority)
        if(len(queue)>0):
            #print("[LCD] Trovato un messaggio con priorita'",priority)
            next_message=queue[0]
            next_message_priority=priority
            break
    #print("[LCD] Il messaggio che ho trovato e'",next_message,next_message_priority)
    return (next_message, next_message_priority)
def _wait_for(condition,predicate,timeout=-1):
    """
    PRE: La funzione deve essere chiamata quando si possiede il LOCK associato alla variabile 'condition'.
    Si mette in attesa di una condizione che verrà notificata alla variabile condizione 'condition'.
    Richiede in ingresso un predicato associato alla condizione da verificare.
    - Se il timeout è specificato allora l'attesa termina:
    1)Se il predicato è vero
    2)Se il timeout è scaduto INDIPENDENTEMENTE dal valore del predicato
    - Se timeout=-1 allora l'attesa termina quando e SOLO se il predicato è vero, ovvero si comporta
    come il metodo condition.wait_for(predicate) (fare riferimento alla documentazione Zerynth).
    La funzione restituisce True se è terminata a causa di predicato vero oppure False se è terminata a
    seguito della scadenza del timeout (quando specificato).
    """
    # NOTA BENE: in condition.wait_for(predicate,timeout) timeout è il tempo oltre il quale non è più necessario
    # attendere una notify per superare il blocco. TUTTAVIA il predicato deve SEMPRE essere vero per permettere 
    # di superare la wait_for(). Pertanto NON è il metodo che fa al caso nostro.

    # Solo se il timeout non è stato specificato la funzione si comporta esattamente come il metodo condition.wait_for()
    # ovvero controlla il predicato ogni volta che viene chiamata condition.notify() da altri thread e ritorna solo
    # quando il predicato diventa vero. Se il predicato è già vero ritorna immediatamente.
    if timeout == -1:
        return condition.wait_for(predicate) 

    remaining_time = timeout
    timer=timers.Timer()
    timer.start()
    while not predicate(): #esce dall'attesa se la condizione è soddisfatta
        #print("Timer.get=",timer.get())
        remaining_time = remaining_time - timer.get() #Il tempo rimanente è pari al tempo rimanente precedente - il tempo trascorso dall'ultimo calcolo
        timer.reset() #Ricomincio a contare il tempo
        if remaining_time<=0: #Se il timeout è già scaduto restituisce False
            timer.destroy()
            return False
        #print("Condizione non soddisfatta. Tempo rimanente:",remaining_time)
        if condition.wait(timeout=remaining_time) == False: #La wait termina a causa della scadenza del timeout
            timer.destroy()
            return False #restituisce False se scade il timeout
    return True #Se arriva qui la condizione è stata soddisfatta e restituisce True

def _check_preemption_elegibility():
    """
    PRE: La funzione deve essere chiamata quando si possiede il LOCK associato alla variabile condition DISPLAY_QUEUE_UPDATED.
    Controlla se il prossimo messaggio nella coda ha diritto di prelazione sul messaggio che
    attualmente si sta visualizzando sul display.
    Normalmente un messaggio ha diritto di prelazione solo se è a priorità strettamente maggiore di quello corrente.
    - Un messaggio in modalità retain ha diritto di prelazione su un qualunque messaggio con la stessa priorità.
    - Un messaggio in modalità retain può essere soggetto a prelazione anche da parte di un messaggio con la stessa priorità.
    Nota:   0: priorità massima
            1: priorità media
            2: priorità bassa
    """
    global curr_message,curr_message_priority
    #print("[LCD] _check_preemption_elegibility start")
    #print("[LCD] _check_preemption_elegibility start global variables imported",curr_message,curr_message_priority)
    (next_message, next_message_priority) = get_next_message()
    #print("[LCD] _check_preemption_elegibility _get_next_message returns:",next_message,next_message_priority)
    #print("[LCD] _check_preemption_elegibility curr_message_priority:",curr_message_priority)
    if next_message == None: #Se la coda è vuota non esercitare prelazione
        return False
    if next_message.retain and curr_message_priority == next_message_priority: #Un messaggio in modalità retain ha diritto di prelazione su un qualunque messaggio con la stessa priorità. (Quick entering rule)
        return True
    if curr_message.retain == True: #Un messaggio in modalità retain può essere soggetto a prelazione anche da parte di un messaggio con la stessa priorità! (Quick exiting rule)
        return next_message_priority <= curr_message_priority
    return next_message_priority < curr_message_priority #Normalmente invece può esercitare prelazione solo un messaggio a priorità strettamente maggiore di un altro"""

def _check_next_message():
    """
    PRE: La funzione deve essere chiamata quando si possiede il LOCK associato alla variabile condition DISPLAY_QUEUE_UPDATED.

    """
    x = get_next_message()[0]
    #print("_check_next_message",x)
    return x != None
common.STATE_LOCK.acquire()
(curr_message,curr_message_priority)=get_next_message()
common.STATE['display-queue'][curr_message_priority].pop(0)
common.STATE_LOCK.release()

def lcd_manager_thread():
    """
        Si occupa di scrivere sul display il contenuto di STATE['display-message']
    """
    global curr_message,curr_message_priority
    print("[LCD] LCD Manager online")
    LCD=lcd_driver.LCD(addr=0x27)
    LCD.disable_cursor()
    display_queue=common.STATE['display-queue']
    retain_mode=False
    # Normalmente solo i messaggi a priorità maggiore del messaggio attuale possono fare prelazione su
    # di esso.
    # Se il messaggio attuale è in modalità retain allora non ha una scadenza ma può essere soggetto
    # a prelazione anche da parte di un messsaggio della stessa priorità! Se così non fosse, i messaggi
    # a priorità massima con retain=True non sarebbero mai rimossi dal display!
    
    # Se in modalità retain mantiene il messaggio corrente finché un messaggio con priorità maggiore 
    # o uguale non sostituisce quello attuale
    # Nota: solo un messaggio con retain=False, dopo un tempo min_time può essere sostituito da un 
    # messaggio a priorità minore (quando non ci sono messaggi a priorità maggiore o uguale). Un
    # messaggio con retain=True non può MAI essere sostituito da un messaggio a priorità minore ma
    # solo da uno a priorità maggiore O UGUALE.
    # Un messaggio in modalità retain non può essere sostituito dal messaggio di default
    
    while True:
        print("[LCD] Stampo",curr_message)
        LCD.clear_and_print(message_type_map[curr_message.msg_type] % curr_message.args) #Stampo il messaggio in base al tipo e ci inserisco gli eventuali parametri
        #print("[LCD] Acquisisco il lock")
        common.STATE_LOCK.acquire()
        #print("[LCD] Lock acquisito")
        timeout=curr_message.min_time
        if retain_mode:
            timeout=-1
        #print("[LCD] Timeout",timeout)
        _wait_for(common.DISPLAY_QUEUE_UPDATED,_check_preemption_elegibility,timeout=timeout) #Aspetta un messaggio che ha diritto di prelazione
        #print("[LCD] Fine dell'attesa")
        # Idea: cond verifica se c'è un messaggio elegibile in base anche a retain mode mentre timeout 
        # è il min_time del message che ho mostrato. Forse se retain=True dev'essere timeout=-1 (?)
        (curr_message,curr_message_priority)=get_next_message()
        if not _check_next_message(): #Non c'è nessun messaggio in coda
            if default_message == False: #Non è stato impostato un messaggio di default
                print("[LCD] Nessun altro messaggio nella coda, ne aspetto uno")
                common.DISPLAY_QUEUE_UPDATED.wait_for(_check_next_message) #Aspetta un qualunque messaggio nella coda
                (curr_message,curr_message_priority)=get_next_message()
                print("[LCD] Nuovo messaggio nella coda!",curr_message,curr_message_priority)
            else: #È stato impostato un messaggio di default
                print("[LCD] Nessun altro messaggio nella coda, invio il messaggio di default")
                common.STATE_LOCK.release() #Il lock va rilasciato perché dispatch_message() è implicitamente thread safe
                dispatch_message(_get_default_message(),2)
                common.STATE_LOCK.acquire()
                (curr_message,curr_message_priority)=get_next_message()
        display_queue[curr_message_priority].pop(0)
        retain_mode = curr_message.retain
        common.STATE_LOCK.release()

def dispatch_message(message,priority=2):
    """
    Inserisce un nuovo messaggio nella coda di priorità.
    La funzione è thread safe pertanto non si deve possedere il lock associato alla variabile condition DISPLAY_QUEUE_UPDATED.
    """
    #print("dispatch_message",message,priority)
    common.DISPLAY_QUEUE_UPDATED.acquire()
    display_queue=common.STATE['display-queue']
    display_queue[priority].append(message)
    common.DISPLAY_QUEUE_UPDATED.notify_all()
    common.DISPLAY_QUEUE_UPDATED.release()

def _get_default_message():
    """
    Restituisce il messaggio da mostrare quando non c'è niente nella coda di priorità:
    - Se l'allarme è disattivato mostra il numero di dispositivi connessi
    - Se l'allarme è attivato mostra la causa di attivazione
    Il messaggio di default dev'essere inviato in modalità retain affinché rimanga sul display
    finché non è sostituito da un nuovo messaggio.
    La funzione è thread safe pertanto non si deve possedere il lock associato alla variabile condition DISPLAY_QUEUE_UPDATED.
    """
    common.STATE_LOCK.acquire()
    if common.STATE['alarm']: #Se l'allarme è attivo recupera il messaggio con la causa dell'attivazione
        message = common.STATE['alarm-message']
    else: #Se l'allarme è disattivo mostra il numero di dispositivi connessi
        devices_number=str(common.STATE['connected-devices-number'])
        message = common.Message('default',3000,args=('ENABLED   ' if common.STATE['alarmed'] else 'DISABLED  ',devices_number),retain=True)
    common.STATE_LOCK.release()
    return message