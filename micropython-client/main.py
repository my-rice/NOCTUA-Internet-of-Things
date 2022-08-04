from umqttsimple import MQTTClient
from machine import Pin
import utime
from machine import Timer

#spengo il led di stato
led_pin.value(0)

#set del pin in base a quanto indicato sul file JSON
if type_IN=="IN":
  button_pin=Pin(2,Pin.IN)  
elif type_IN=="PULL_UP":
  button_pin=Pin(2,Pin.IN,Pin.PULL_UP)

#funzione per la gestione dei fronti
i=0
def on_click(p):
  global i
  global last_value
  #prendo il valore attuale del sensore
  current_value= button_pin.value()
  #se sono connesso alla rete
  if station.isconnected() == True:

  # gestione dei fronti di salita
    if'RISING' in type_EDGE and current_value==1 and last_value==0:
      led_pin.value(1)
      print(i, 'Rising edge detected, publishing...')
      i=i+1
      value=value_1_stato_attuale
      payload={"session-id": session_id, "value": value}
      #pubblico fronte rilevato
      c.publish(topic_value,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON 
      utime.sleep_ms(led_on_time_ms)
      led_pin.value(0)

  # gestione dei fronti di discesa
    elif 'FALLING' in type_EDGE and current_value==0 and last_value==1:
      led_pin.value(1)
      print(i, 'Falling edge detected, publishing...')
      i=i+1
      value=value_0_stato_attuale
      payload={"session-id": session_id, "value": value}
      #pubblico fronte rilevato
      c.publish(topic_value,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON 
      utime.sleep_ms(1000)
      led_pin.value(0)

  #aggiorno il valore precedente
    last_value=current_value

#timer per la verifica dei fronti
#evita problemi del debounce
tim = Timer(-1)
tim.init(period=period_edge_control_ms, mode=Timer.PERIODIC, callback=on_click)

#verifica la connessione e l'arrivo dei topic di broadcast
while True:
  if station.isconnected() == False:
    #se non sono più connesso provo a riconettermi
    led_pin = machine.PWM(machine.Pin(0), freq=4)
    led_pin.duty(512)
    print("connection problem, trying to reconnect")
    station.connect(ssid, password)
    k=0
    while station.isconnected() == False:
      print("trying to reconnect")
      k=k+1
      
      utime.sleep_ms(1000)
      if k>=300:
        led_pin.deinit()
        raise Exception
      
    print('Connection successful')
    print(station.ifconfig())

    #ricavo il nuovo session id 
    try:
      f=open('session_id','r')
      session_id=int(f.read())
      f.close()
    except OSError:
      print("file non aperto")

    print("old session id:", session_id)
    session_id=(session_id + 1)%100

    try:
      f= open('session_id', 'w')
      f.write(str(session_id))
      f.close()
    except OSError:
      print("non riesco a scrivere")

    print("new session id:", session_id)
    
    #collegamento a MQTT con il nuovo session id
    value="DISCONNECTED"
    payload={"session-id": session_id, "value": value}
    c.set_last_will(topic_disconnect,json.dumps(payload), qos=1)
    
    c.connect()
    value="CONNECTED"
    payload={"session-id": session_id, "value": value}
    c.publish(topic_connect,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON  

    led_pin.deinit()
    led_pin=Pin(0,Pin.OUT)

  else:
    #una volta al secondo
    utime.sleep_ms(1000)
    try:
      #invio un ping al server per non risultare disconesso in caso non vengano inviati messaggi
      c.ping()
      #controllo i messaggi di BROADCAST
      c.check_msg()
    except OSError:
      print("errore dal check message PING o dal PING con il server")
