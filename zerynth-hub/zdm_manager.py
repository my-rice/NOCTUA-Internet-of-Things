from zdm import zdm        #modulo zdm
import common


#TAG = DOORS
#PAYLOAD = {
#   "room1":{
#       "device-id":"OPEN",
#       "device-id2":"CLOSED"
#   },
#   "room2":{
#       "device-id":"CLOSED"
#   }
# }

#TAG = LOG
#payload={"type":log_type,"message":message}

#TAG = LOG
#payload={"type":"ALARMED","message":True/False}

#TAG = LOG
#payload={"type":"ALARM","message":True/False}

#TAG = MOVEMENT
#PAYLOAD = {
#   "device-id":"12332321",
#   "room":""
# }

#TAG = DEVICES
#PAYLOAD = {
# }
def job_enable_alarm(agent, arguments):     #Job per armare l'allarme
    import behaviours
    print("[ZDM] Enable alarm job started")
    behaviours._set_alarmed()

def job_disable_alarm(agent, arguments):    #Job per disarmare l'allarme
    import behaviours
    print("[ZDM] Disable alarm job started")
    behaviours._set_not_alarmed()

def send(tag, payload):
    global agent
    try:
        print("[ZDM] Trying to publish payload",payload,"with tag",tag)
        agent.publish(payload, tag=tag)
    except MQTTPublishTimeout as e:
        print("[ZDM] Publishing failed")
    print("[ZDM] Data published successfully.")

def send_log(log_type,message):
    send("LOG",{"type":log_type,"message":message})

def initialize():
    global agent
    config=zdm.Config(keepalive=10,
       reconnect_after=3000,
       network_timeout=60000,
       clean_session=True,
       qos_publish=1,
       qos_subscribe=1) 
    agent=zdm.Agent(cfg=config,jobs={"enable_alarm":job_enable_alarm,"disable_alarm":job_disable_alarm})
    agent.start()
    print("[ZDM] Agent started successfully. Connected:",agent.connected(),", Online:",agent.online())
    send_log("ALARM",False)
    send_log("ALARMED",False)




