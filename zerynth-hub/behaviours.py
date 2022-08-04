#Un client (ESP01) è un sensore o un attuatore 
#L'hub è la scheda zerynth
#NOCTUA/{TYPE}/{ID}/VALUE
#NOCTUA/{TYPE}/{ID}/CONNECTED
#NOCTUA/{TYPE}/{ID}/DISCONNECTED
#NOCTUA/BROADCAST
import time
import json
import common
import buzzer
import zdm_manager
import dispatcher
import gpio

connected_devices = common.STATE['connected-devices']
disconnected_devices = common.STATE['disconnected-devices']
#Un Client (ESP01) è un sensore o un attuatore remoto
class Client:
    def __init__(self,id,client_type,client_session_id):
        self.id=id
        self.type=client_type
        if id in common.ROOMS:
            self.room=common.ROOMS[id]
        else:
            self.room='default'
        self.last_seen=time.localtime()
        self.client_session_id=client_session_id

    def __str__(self):
        return "Client{id: "+self.id+", type: "+str(self.type)+", room: "+self.room+", last_seen: "+str(self.last_seen.get_unix())+"}"
    def update_last_seen(self):
        self.last_seen=time.localtime()

def print_message_info(c, topic, message):
    """Stampa le informazioni contenute nel topic e nel payload"""
    print("[MQTT] Received on",topic,"message",message)

def get_type(string):
    """
    PRE:Il topic sarà in questa forma NOCTUA/{TYPE}/{ID}/VALUE.
    Estrae {TYPE} dal topic.
    Es: NOCTUA/DOOR/0x10c/VALUE -> DOOR
    """
    return string.split('/')[1]
def get_id(string):
    """
    PRE:Il topic sarà in questa forma NOCTUA/{TYPE}/{ID}/VALUE.
    Estrae {ID} dal topic.
    Es: NOCTUA/DOOR/0x10c/VALUE -> 0x10c
    """
    return string.split('/')[2]

#Il client dice se è connesso al server MQTT
def on_client_connect(c, topic, message):
    """
    Callback per il topic NOCTUA/{TYPE}/{ID}/CONNECTED
        - c: stringa che identifica il client MQTT. NON è l'id dei Client (client NOCTUA)
        - topic: stringa che rappresenta il topic MQTT sul quale è stato pubblicato il messaggio
        - message: è il payload, cioè il contenuto del messaggio MQTT
    """
    print("[CL] Topic type:",type(topic),"Message type:",type(message))
    if type(topic) is not PSTRING or type(message) is not PSTRING:
        print("[CL] Incoherent data type for topic or payload. Ignoring connect message.")
        #print("[CL] Trying to print topic!")
        #print(str(topic))
        return
    global connected_devices, disconnected_devices
    #print_message_info(client, topic, message) #DEBUG
    client_id = get_id(topic)
    #client_type=Type[get_type(topic)]
    client_type=get_type(topic)
    #Ricavo il client_session_id da messagge interpretando il json
    payload = json.loads(message)
    client_session_id = payload['session-id']

    #Se mi arriva un messaggio di connect e il dispositivo è già connesso, devo aggiornare il messaggio di ID con quello nuovo
    _connect_device(client_id,client_type,client_session_id)
    print("[CL] Il dispositivo e' connesso con payload",payload,"e session-id",client_session_id)
    _print_current_state()

#Il client dice se si è sconnesso
def on_client_death(c, topic, message):
    """
    Callback per il topic NOCTUA/{TYPE}/{ID}/DISCONNECTED. Si occupa di gestire la disconnessione
    di un Client dal sistema. Tale messaggio viene solitamente ricevuto come last will and testament
    di un Client che non risponde.
        - c: stringa che identifica il client MQTT. NON è l'id dei Client (client NOCTUA)
        - topic: stringa che rappresenta il topic MQTT sul quale è stato pubblicato il messaggio
        - message: è il payload, cioè il contenuto del messaggio MQTT
    """
    print("[CL] Topic type:",type(topic),"Message type:",type(message))
    if type(topic) is not PSTRING or type(message) is not PSTRING:
        print("[CL] Incoherent data type for topic or payload. Ignoring disconnect message.")
        #print("[CL] Trying to print topic!")
        #print(str(topic))
        return
    global connected_devices,disconnected_devices
    #print_message_info(client, topic, message)
    client_id = get_id(topic)

    #Recupero il session-id dal payload del messaggio
    payload = json.loads(message)
    client_session_id = payload['session-id']

    #Acquisisco il mutex sullo stato del sistema
    common.STATE_LOCK.acquire()

    #Se mi arriva un messaggio di disconnect e il dispositivo è connesso, devo controllare se il session ID è quello giusto
    if client_id not in connected_devices:
        common.STATE_LOCK.release()
        print("[CL] Disconnected client asked for disconnection! Ignoring it.")
        return

    #A questo punto client_id è sicuramente nei connected_devices
    if client_session_id != connected_devices[client_id].client_session_id: #Se il client_session_id è diverso da quello attuale allora significa che la disconnessione non è riferita al client attualmente in funzione
        common.STATE_LOCK.release()
        print("[CL] Connection message with incoherent session-id received. Ignoring it.")
        return

    #Se arrivo qui il dipositivo va effettivamente disconnesso dal sistema
    #print("[CL] Disconnetto il dispositivo",client_id,"dal sistema")
    client = connected_devices.pop(client_id)
    disconnected_devices.update({client_id:client})

    #Aggiorno il numero di dispositivi connessi
    common.STATE['connected-devices-number'] = common.STATE['connected-devices-number']-1
    #Rilascio il mutex
    common.STATE_LOCK.release()
    _showMessageDisconnected(client)
    _print_current_state() #thread safe

def on_client_message(c, topic, message):
    """
    Callback per il topic NOCTUA/{TYPE}/{ID}/VALUE. Si occupa di gestire la disconnessione di 
    un Client dal sistema. Tale messaggio viene solitamente ricevuto come last will and testament
    di un Client che non risponde.
        - c: stringa che identifica il client MQTT. NON è l'id dei Client (client NOCTUA)
        - topic: stringa che rappresenta il topic MQTT sul quale è stato pubblicato il messaggio
        - message: è il payload, cioè il contenuto del messaggio MQTT
    """
    print("[CL] Topic type:",type(topic),"Message type:",type(message))
    if type(topic) is not PSTRING or type(message) is not PSTRING:
        print("[CL] Incoherent data type for topic or payload. Ignoring value message.")
        #print("[CL] Trying to print topic!")
        #print(str(topic))
        return
    global connected_devices,disconnected_devices
    #print_message_info(client, topic, message)
    
    client_id=get_id(topic)
    client_type=get_type(topic)
    #print("client_id:",client_id,"client_type:",client_type)
    
    #Recupero il session-id dal payload del messaggio
    payload = json.loads(message)
    client_session_id = payload['session-id']

    #Acquisisco il mutex sullo stato del sistema
    common.STATE_LOCK.acquire()

    #Se il client_id non è all'interno dei dispositivi connessi, lo devo connettere
    if client_id not in connected_devices:
        common.STATE_LOCK.release() #Va rilasciato il mutex, perchè la connect_device è thread-safe
        print("[CL] Received message from disconnected devie. Proceeding to connect it...")
        _connect_device(client_id,client_type,client_session_id)
        _print_current_state()
        common.STATE_LOCK.acquire()
    
    client=connected_devices.get(client_id) #Il device è sicuramente connesso
    common.STATE_LOCK.release()
    
    # CENTRAL LOGIC CORE
    # In questa parte del codice viene effettivamente gestito il comportamento del sistema 
    # in base agli input ricevuti dai diversi sensori

    if client_type == 'DOOR': #sensore di porta o finestra
        #Interpreto il payload del messaggio
        payload = json.loads(message)
        door_state = payload['value']
        if door_state == 'OPEN': #porta aperta
            print("[CL] Door opened:",client_id,"in room",client.room)
            
        elif door_state =='CLOSED': #porta chiusa
            print("[CL] Door closed:",client_id,"in room",client.room)
        
        common.STATE_LOCK.acquire()
        common.STATE['doors'][client.room].update({client_id:door_state})
        #print("[CL] New doors state:",common.STATE['doors'])
        # Invio i dati alla ZDM
        zdm_payload = common.STATE['doors']
        zdm_manager.send("DOORS", zdm_payload)
        common.STATE_LOCK.release()
        # Decido l'azione da intraprendere sulla base dello stato del sistema e del messaggio inviato dal sensore
        if door_state == "OPEN":
            if _check_alarmed(): #Se il sistema è armato scatta l'allarme
                _enable_siren(reason=client_type,arg=client.room)
            else: #Se il sistema non è allarmato notifica l'utente sul display
                _showMessageDoorOpened(client)
    # Caso in cui un sensore di movimento ad infrarossi invia un messaggio:
    elif client_type == 'MOVEMENT':
        #Interpreto il payload del messaggio
        payload = json.loads(message)
        movement_state = payload['value']

        #Se il sensore non invia un messaggio di "MOVEMENT" va ignorato. Questa cosa può accedere a seguito dell'invio di un PING da parte della Central Logic
        if movement_state != "MOVEMENT":
            return

        print("[CL] Movement deteced in room",client.room,"from device",client.id)  
        #Invio i dati alla ZDM
        zdm_payload = {
            "device-id":client.id,
            "room":client.room
        }
        zdm_manager.send("MOVEMENT", zdm_payload)
        
        #Decido l'azione da intraprendere sulla base dello stato del sistema
        if _check_alarmed():
            _enable_siren(reason=client_type,arg=client.room)
        else:
            _showMessageMovement(client)
    else:
        print("[CL] Error: Can't detect message type!")

#funzioni private iniziano con _
def _check_alarmed():
    """Controlla se il sistema è armato. Restituisce True se il sistema è armato, altrimenti False.
    La funzione è thread safe"""
    #print(STATE['alarm'])
    common.STATE_LOCK.acquire()
    alarmed=common.STATE['alarmed']
    common.STATE_LOCK.release()
    return alarmed

def _set_alarmed():
    """La funziona arma il sistema."""
    common.STATE_LOCK.acquire()
    if common.STATE['alarmed'] == True: #Se è già armato non fare nulla
        common.STATE_LOCK.release()
        print("[CL] System already armed!")
        return
    common.STATE['alarmed']=True #Il sistema è armato
    zdm_manager.send_log("ALARMED",True)
    common.STATE_LOCK.release()
    dispatcher.dispatch_message(common.Message('alarmed',3000,retain=False),priority=0)

def _set_not_alarmed():
    """La funziona disarma il sistema."""
    common.STATE_LOCK.acquire()
    if common.STATE['alarm'] == True: #Se l'allarme è attivo va disattivato
        common.STATE_LOCK.release()
        _disable_siren()
        common.STATE_LOCK.acquire()
    if common.STATE['alarmed'] == False: #Se il sistema è già disarmato rilascia il lock e non fa nulla
        common.STATE_LOCK.release()
        print("[CL] System already disarmed!")
        return
    common.STATE['alarmed']=False #Disarma il sistema
    zdm_manager.send_log("ALARMED",False)
    common.STATE_LOCK.release()
    dispatcher.dispatch_message(common.Message('not-alarmed',3000,retain=False),priority=0)

def _enable_siren(reason="Unknown",arg="Unknown"):
    """
    Attiva l'allarme. Viene attivato il segnale acustico ed notifica la ZDM dell'attivazione dell'allarme.
    Sul diplay è mostrata la causa che ha scatenato l'allarme con priorità alta.
    """
    print("[CL] ENABLING SIREN!")
    common.STATE_LOCK.acquire()
    if common.STATE['alarm'] == True: #Se l'allarme è già attivato non fa nulla
        common.STATE_LOCK.release()
        print("[CL] Alarm is already enabled!")
        return
    common.STATE['alarm'] = True #Attiva l'allarme
    common.STATE_LOCK.release()
    buzzer.enable_buzzer() #Attiva il buzzer
    zdm_manager.send_log("ALARM",True)
    if reason=='MOVEMENT':
        message = common.Message('alarm-movement',0,args=(arg),retain=True)
        common.STATE_LOCK.acquire()
        common.STATE['alarm-message']=message
        common.STATE_LOCK.release()
        dispatcher.dispatch_message(message,priority=0)
        gpio.set(common.RED_LED,HIGH)
    elif reason=='DOOR':
        message = common.Message('alarm-door',0,args=(arg),retain=True)
        common.STATE_LOCK.acquire()
        common.STATE['alarm-message']=message
        common.STATE_LOCK.release()
        dispatcher.dispatch_message(message,priority=0)
        gpio.set(common.RED_LED,HIGH)

def _disable_siren():
    """
    Disattiva l'allarme. Viene disattivato il segnale acustico ed notifica la ZDM della 
    disattivazione dell'allarme.
    """
    common.STATE_LOCK.acquire()
    if common.STATE['alarm'] == False: #Se l'allarme è già disattivato non fa nulla
        common.STATE_LOCK.release()
        print("[CL] Alarm is already disabled!")
        return
    common.STATE['alarm'] = False #Disattiva l'allarme
    common.STATE_LOCK.release()
    print("Sirena disattivata")
    buzzer.disable_buzzer()
    zdm_manager.send_log("ALARM",False)
    gpio.set(common.RED_LED,LOW)

def _print_current_state():
    """La funzione è thread safe, quando viene chiamata non si deve possedere il lock"""
    global connected_devices, disconnected_devices
    common.STATE_LOCK.acquire()
    print("[CL] Number of connected devices:",common.STATE['connected-devices-number'])
    print("[CL] Connected devices:")
    for (key,value) in connected_devices.items():
        print(key,":",value)
    print("[CL] Disconnected devices:")
    for (key,value) in disconnected_devices.items():
        print(key,":",value)
    common.STATE_LOCK.release()

def _connect_device(client_id,client_type,client_session_id):
    """
    Connette un client al sistema. Gestisce i casi in cui:
    - il dispositivo si connette per la prima volta
    - il dispositivo si era già connesso in passato
    - il dispostivio è già connesso
    Gli argomenti della funzione sono:
    - client_id: id del client
    - client_type: tipo del client
    - client_session_id: session_id con cui il client ha richiesto la connessione
    Se il client è già connesso e si connette con session_id più recente, aggiorna il session_id.
    La funzione è thread safe, quando viene chiamata non si deve possedere il lock.
    """
    global connected_devices,disconnected_devices
    common.STATE_LOCK.acquire()
    if client_id in connected_devices: #Il dispositivo è già connesso
        print("[CL] Client",client_id,"already connected. Updating session id:",client_session_id)
        client=connected_devices[client_id]
        client.client_session_id = client_session_id # Aggiorno l'ID della sessione 
        client.update_last_seen() #Aggiorna last_seen
        common.STATE_LOCK.release()
        return
    elif client_id in disconnected_devices: #Entra qui se c'è già l'istanza in disconnected-devices
        client = disconnected_devices.pop(client_id)
        #Aggiorno il client_session_id
        client.client_session_id = client_session_id
        print("[CL] Welcome back",client_id,". Inserting with session_id:",client_session_id)
        client.update_last_seen() #Aggiorna last_seen
        connected_devices.update({client.id:client})
        #Aggiorno il numero di dispositivi connessi
        common.STATE['connected-devices-number'] = common.STATE['connected-devices-number']+1
        #Mostra il messaggio sul display
    else: #Entra qui se il client non è mai stato inserito prima
        print("[CL] Client",client_id,"connected for the first. Inserting with session_id:")
        #Definisco una nuova istanza di Client
        client = Client(client_id,client_type,client_session_id)
        connected_devices.update({client_id:client})
        common.STATE['connected-devices-number'] = common.STATE['connected-devices-number']+1
    common.STATE_LOCK.release()
    _showMessageConnected(client)

def _showMessageConnected(client):
    """
    La funzione mostra il messaggio di dispotivio connesso sul display. 
    - client: il dipositivo che si è connesso
    """
    #print("_showMessageConnected",client)
    msg = client.type + ' SENSOR'
    for i in range(len(msg),16): #Aggiungi un numero sufficiente di spazi
        msg = msg + ' '
    dispatcher.dispatch_message(common.Message('device-connected',1500,args=(msg)),priority=2)
    dispatcher.dispatch_message(common.Message('in-room',2000,args=(client.room)),priority=2)

def _showMessageDisconnected(client):
    """
    La funzione mostra il messaggio di dispotivio disconnesso sul display. 
    - client: il dipositivo che si è disconnesso
    """
    #print("_showMessageDisconnected",client)
    msg = client.type + ' SENSOR'
    for i in range(len(msg),16): #Aggiungi un numero sufficiente di spazi
        msg = msg + ' '
    dispatcher.dispatch_message(common.Message('device-disconnected',1500,args=(msg)),priority=2)
    dispatcher.dispatch_message(common.Message('in-room',2000,args=(client.room)),priority=2)

def _showMessageDoorOpened(client):
    """
    La funzione mostra il messaggio di porta aperta sul display. 
    - client: il dipositivo che ha rilevato la porta aperta
    """
    dispatcher.dispatch_message(common.Message('door-open-detected',1500),priority=1)
    dispatcher.dispatch_message(common.Message('in-room',2000,args=(client.room)),priority=1)

def _showMessageMovement(client):
    """
    La funzione mostra il messaggio di movimento sul display. 
    - client: il dipositivo che ha rilevato il movimento
    """
    dispatcher.dispatch_message(common.Message('movement-detected',1500),priority=1)
    dispatcher.dispatch_message(common.Message('in-room',2000,args=(client.room)),priority=1)
