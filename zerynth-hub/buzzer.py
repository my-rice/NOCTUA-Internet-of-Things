import gpio
import pwm
#Dal datasheet la frequenza arriva a 4096Hz

pin = D5
gpio.mode(pin,OUTPUT) #Setto il pin del buzzer in modalità output
frequency = 4000 #Definisco la frequenza di partenza
period_us = int((1/frequency)*1000000)
duty_cycle = 0.5
t_on_us = int(duty_cycle * period_us)
print("[BUZ] Buzzer module loaded. Frequency:",frequency,"Period (us):",period_us,"Duty cycle:",duty_cycle,"t_on (us):",t_on_us)
def enable_buzzer():
    print("[BUZ] Enabling buzzer")
    pwm.write(pin,period_us,t_on_us,time_unit=MICROS)

def disable_buzzer():
    print("[BUZ] Disabling buzzer")
    pwm.write(pin,0,0,time_unit=MICROS)