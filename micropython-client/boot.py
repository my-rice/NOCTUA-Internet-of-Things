import utime
from umqttsimple import MQTTClient
import ubinascii
import machine
from machine import Pin, PWM
import micropython
import network
import esp
import json
import os

session_id=0

#apertura del file locale per visionare l'ultimo session id
try:
  f=open('session_id','r')
  session_id=int(f.read())
  f.close()
except OSError:
  print("file non aperto")

#creazione nuovo session id con aggiunta di un'unità    
session_id=(session_id + 1)%100

#scrittura del nuovo session id sul file locale
try:
  f= open('session_id', 'w')
  f.write(str(session_id))
  f.close()
except OSError:
  print("non riesco a scrivere")

#inizializzazione del led in PWM per ricerca rete internet
led_pin = machine.PWM(machine.Pin(0), freq=4)

#aperture file json da cui prelevare informazioni sulla configurazione
with open('config.json') as file:
  CONFIG = json.load(file)
#print(CONFIG,CONFIG["ssid"])

#INPUT FEATURES SENSOR
type_IN= CONFIG["type_IN"]
type_EDGE =CONFIG["type_EDGE"] #'RISING' or 'FALLING' or ['RISING','FALLING'] 
period_edge_control_ms= CONFIG["period_edge_control_ms"] #ogni quanto verifico fronte
led_on_time_ms= CONFIG["led_on_time_ms"] #durata accensione led'''

#CONNECT WI-FI
ssid = CONFIG["ssid"]
password = CONFIG["password"]
mqtt_server = CONFIG["mqtt_server"]
#funzione per creare id univoci
client_id = CONFIG["client_id"]
#mqtt credenziali
mqtt_user= CONFIG["mqtt_user"]
mqtt_password= CONFIG["mqtt_password"]
topic_pub= CONFIG["topic_pub"]
type_SENSOR= CONFIG["type_SENSOR"]
#messagi valori 
value_0_stato_attuale=CONFIG["value_0_stato_attuale"]
value_1_stato_attuale=CONFIG["value_1_stato_attuale"]

#creazione dei topic
topic_connect= str(topic_pub) + "/" + str(type_SENSOR) + "/" + client_id + "/CONNECTED"
topic_disconnect= str(topic_pub) + "/" + str(type_SENSOR) + "/" + client_id + "/DISCONNECTED"
topic_value= str(topic_pub) + "/" + str(type_SENSOR) + "/" + client_id + "/VALUE"

#set dell'ultimo valore
last_value=-1

#risposta al messaggio di broadcast con stato connessione e stato valore letto
def broadcast(topic,msg):
  if topic == b'NOCTUA/BROADCAST' and msg == b'PING':
    print("rispondo al ping, con session_id:", session_id, "e stato attuale:", last_value)
    value="CONNECTED"
    payload={"session-id": session_id, "value": value}
    c.publish(topic_connect,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON
    if last_value==0:
      value=value_0_stato_attuale
      payload={"session-id": session_id, "value": value}
      c.publish(topic_value,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON 
    elif last_value==1:
      value=value_1_stato_attuale
      payload={"session-id": session_id, "value": value}
      c.publish(topic_value,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON


last_message = 0
message_interval = 5
counter = 0

#configurazione rete internet
station = network.WLAN(network.STA_IF)
station.active(True)
station.connect(ssid, password)

#connessione alla rete
i=0
led_pin.duty(512)
while station.isconnected() == False:
  utime.sleep_ms(1000)

  print("trying to connect")
  i=i+1
  if i>=30:
    led_pin.deinit()
    led_pin=Pin(0,Pin.OUT)
    raise Exception
#dopo la coneessione deiniziallizzo led come PWM e lo uso per i valori sensori
led_pin.deinit()
led_pin=Pin(0,Pin.OUT)
print('Connection successful')
print(station.ifconfig())

#definizione client
c = MQTTClient(client_id, mqtt_server,user=mqtt_user,password=mqtt_password,keepalive=5) #keep live in sec
value="DISCONNECTED"
payload={"session-id": session_id, "value": value}

#connessione al server mqtt
c.set_last_will(topic_disconnect,json.dumps(payload), qos=1)
c.set_callback(broadcast)
c.connect()

#prima pubblicazione per indicare che ci si è connessi
value="CONNECTED"
payload={"session-id": session_id, "value": value}
c.publish(topic_connect,json.dumps(payload), qos=1) #converte qualsiasi oggetto in una stringa in formatoJSON 
#sottoscrizione al topic di BROADCAST
c.subscribe("NOCTUA/BROADCAST")