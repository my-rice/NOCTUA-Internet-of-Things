from networking import wifi
from protocols import mqtt
import common
import json
import fs
import threading
import behaviours
import dispatcher
import password_manager
import zdm_manager
import gpio

def mqtt_thread():
    try:
        print("[MQTT] Initializing loop...")
        client.loop()
    except Exception as e:
        print("[MQTT] Loop exited with error:",e)

dispatcher.default_message=True #Abilita il messaggio di default
thread(dispatcher.lcd_manager_thread) #Avvia il dispatcher
thread(password_manager.password_manager_thread) #Avvia il gestore del keypad

wifi.configure(ssid = common.CONFIG["WIFI_SSID"], password = common.CONFIG["WIFI_PASSWORD"])
try:
    wifi.start()
    print("[NET] Successfully connected to wireless network\n[NET] Info:",wifi.info())
    client = mqtt.MQTT(common.CONFIG["MQTT_HOST"],common.CONFIG["MQTT_CLIENT_ID"],username=common.CONFIG["MQTT_USER"],password=common.CONFIG["MQTT_PASSWORD"],port=common.CONFIG["MQTT_PORT"],keepalive=5)
    #client.on("#",behaviours.print_message_info,1) #DEBUG
    client.on("NOCTUA/+/+/CONNECTED",behaviours.on_client_connect,qos=1)
    client.on("NOCTUA/+/+/DISCONNECTED",behaviours.on_client_death,qos=1)
    client.on("NOCTUA/+/+/VALUE",behaviours.on_client_message,qos=1)
    client.connect()
    cnt = 0
    while True:
        sleep(5000)
        if client.is_connected():
            break
        cnt += 1
        print("[MQTT] Trying to connect to MQTT broker...", cnt)
        if cnt > 10:
            raise(Exception("Can't connect to MQTT broker"))
    print("[MQTT] Successfully connected to MQTT broker")
    zdm_manager.initialize()
    thread(mqtt_thread) #Avvia il thread MQTT
    client.publish("NOCTUA/BROADCAST", "PING", qos=1, retain=False) #Pubblica il messaggio di PING in broadcast ai sensori
    gpio.set(common.GREEN_LED,HIGH) #Led verde acceso
except WifiBadPassword:
    print("[NET] Error: Bad WiFi Password")
except WifiBadSSID:
    print("[NET] Error: Bad SSID")
except WifiException:
    print("[NET] Error: Generic Wifi Exception")
except Exception as e:
    print("[SYS] Generic exception occurred:",e)
    raise e