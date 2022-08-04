import gpio
import common
import janus
import dispatcher
gpio.mode(D32,INPUT_PULLDOWN)
gpio.mode(D33,INPUT_PULLDOWN)
gpio.mode(D25,INPUT_PULLDOWN)
gpio.mode(D26,INPUT_PULLDOWN)
LCD=janus.LCD(0x27)
sleep(1000)

def button_1():
    print("Dispatch 1:")
    dispatcher.dispatch_message(common.Message('type1','arg',5000,retain=False),2)

def button_2():
    print("Dispatch 2:")
    dispatcher.dispatch_message(common.Message('type2','arg',5000,retain=False),1)

def button_3():
    print("Dispatch 3:")
    dispatcher.dispatch_message(common.Message('type3','arg',5000,retain=False),0)

def button_4():
    print("Dispatch 4:")
    dispatcher.dispatch_message(common.Message('type4','arg',5000,retain=True),0)

gpio.on_rise(D32,button_1,debounce=4,pull=INPUT_PULLDOWN)
gpio.on_rise(D33,button_2,debounce=4,pull=INPUT_PULLDOWN)
gpio.on_rise(D25,button_3,debounce=4,pull=INPUT_PULLDOWN)
gpio.on_rise(D26,button_4,debounce=4,pull=INPUT_PULLDOWN)