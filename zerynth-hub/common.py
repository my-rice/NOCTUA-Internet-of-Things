import threading
import fs
import json
import gpio

#Messaggio mostrabile sul display
class Message():
    def __init__(self,msg_type,min_time,args=(),retain=False):
        self.msg_type=msg_type
        self.args=args
        self.min_time=min_time
        self.retain=retain
    def __str__(self):
        return "Message(type="+self.msg_type+", arg="+str(self.args)+", min_time="+str(self.min_time)+", retain="+str(self.retain)+")"
#Dizionario che mantiene lo stato globale del sistema
STATE = {
    'alarmed':False,
    'alarm':False,
    'connected-devices':{}, #La chiave è connected-devices ed ha come valore un dictionary, che ad ogni chiave associa un Client. 
    'disconnected-devices':{},
    'connected-devices-number':0,
    'display-queue':{ #priority queue
        0:[], #Modalità retain: se attiva il messaggio è sovrascritto solo da 
        1:[],
        2:[Message('greet',5000)]
    },
    'entering-password':False,
    'doors':{
        'default':{}
    },
    'alarm-message':None
}
STATE_LOCK = threading.Lock()
DISPLAY_QUEUE_UPDATED = threading.Condition(lock=STATE_LOCK)


GREEN_LED = D19
RED_LED = D21
gpio.mode(GREEN_LED,OUTPUT)
gpio.mode(RED_LED,OUTPUT)
gpio.set(GREEN_LED,LOW)
gpio.set(RED_LED,LOW)

try:
    print(fs.ls('/zerynth/'))
    fp = fs.open('/zerynth/config.json','r')
    buf=fp.read()
    fp.close()
    CONFIG=json.loads(buf)
    print("[SYS] Succssfully loaded configuration\n[SYS] Config:",CONFIG)
except IOError:
    print("[SYS] Error reading configuration. Can't access file. Aborting...")
    sleep(3000)
except JSONError:
    print("[SYS] Error reading configuration. Bad formatting. Aborting...")
    sleep(3000)

try:
    print(fs.ls('/zerynth/'))
    fp = fs.open('/zerynth/rooms.json','r')
    buf=fp.read()
    fp.close()
    ROOMS=json.loads(buf)
    print("[SYS] Succssfully loaded rooms\n[SYS] Rooms:",ROOMS)
except IOError:
    print("[SYS] Error reading rooms. Can't access file. Aborting...")
    sleep(3000)
except JSONError:
    print("[SYS] Error reading rooms. Bad formatting. Aborting...")
    sleep(3000)

rooms_set = set()
for room in ROOMS.values(): #Estrai tutte le stanze dizionario ROOMS...
    rooms_set.add(room)
    print("for1",room)
STATE_LOCK.acquire()
for room in rooms_set: #...e aggiungile al dizionario STATE['doors']
    print("for2",room)
    STATE['doors'].update({room:{}})
STATE_LOCK.release()