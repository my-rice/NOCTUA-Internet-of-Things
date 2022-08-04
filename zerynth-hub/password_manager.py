import keypad
import common
import dispatcher
import behaviours
entered_password=''
entering_password=common.STATE['entering-password']

def password_manager_thread():
    """
        Legge l'input proveniente dal keypad. Sovrascrive il display-message sia quando
        l'allarme è attivo sia quando è disattivo. Quando inizia la sottomissione della password
        il flag STATE.entering-password è posto a true. Quando questo accade 
        si deve fare in modo che nessun altro thread possa modificare il contenuto del display
        finché non termina la sottomissione della password
    """
    key_pressed = False
    while True:
        key = keypad.read()
        if key != None and not key_pressed:
            print("[KEY] Key pressed:",key)
            key_pressed = True
            _handle(key)
        if key == None:
            key_pressed = False

def _handle(key):
    """
    Gestisce la pressione del tasto key sul keypad.
    """
    global entering_password
    key=str(key)
    common.STATE_LOCK.acquire()
    if entering_password == False:
        entering_password = True
    common.STATE_LOCK.release()
    if key == 'B' or key == 'C' or key == 'D' or key == '#' or key == '*': #Tasti da ignorare
        return
    if key == 'A': #Comando di enter
        if common.CONFIG['SYSTEM_PASSWORD'] == entered_password: #password corretta
            print("[KM] Correct password was entered:",entered_password)
            _toggle_alarmed()
        else: #password errata
            print("[KM] Wrong password was entered:",entered_password)
            dispatcher.dispatch_message(common.Message('wrong-password',3000,retain=False),priority=0)
            common.STATE_LOCK.acquire()
            entering_password = False
            common.STATE_LOCK.release()
        entered_password=''
        return
    if len(entered_password) >= 8: #Un codice PIN non può superare gli 8 caratteri
        return
    
    #print("enterd_password",entered_password)
    #print("key",key)
    #print("str(key)",str(key))
    entered_password = entered_password + key
    dispatcher.dispatch_message(common.Message('password',0,args=(entered_password),retain=True),priority=0)

def _toggle_alarmed():
    if not behaviours._check_alarmed(): #Se non è allarmato
        behaviours._set_alarmed()
    else: #Se è allarmato
        behaviours._set_not_alarmed()
