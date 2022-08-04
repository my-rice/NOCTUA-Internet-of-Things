import gpio

#Dal datasheet: 5,6,7,8 sono le righe e 1,2,3,4 sono le colonne

#Configuro i pin
gpio.mode(D23,OUTPUT) #8 #1a riga
gpio.mode(D22,OUTPUT) #7
gpio.mode(D32,OUTPUT) #6
gpio.mode(D33,OUTPUT) #5
gpio.mode(D25,INPUT_PULLDOWN) #4 #1 colonna
gpio.mode(D26,INPUT_PULLDOWN) #3
gpio.mode(D27,INPUT_PULLDOWN) #2
gpio.mode(D14,INPUT_PULLDOWN) #1

#Matrice di conversione
key_map = [["1","2","3","A"],\
        ["4","5","6","B"],\
        ["7","8","9","C"],\
        ["*","0","#","D"]]

def max_position(res):
    b = 0
    for i in res:
        if i == 1:
            return b
        b+=1
    return -1

#Funzione per tradurre i segnali del keypad 
def read():
    """La funzione scansiona il keypad e restituisce il tasto premuto."""
    #sleep(1000)
    gpio.set(D23,HIGH)
    result=[gpio.get(D25),gpio.get(D26),gpio.get(D27),gpio.get(D14)]
    #print(result)
    if max(result)==1: #Se c'è almeno un valore HIGH
        key=key_map[0][max_position(result)]
        gpio.set(D23,LOW)
        return(key)
    gpio.set(D23,LOW)

    gpio.set(D22,HIGH)
    result=[gpio.get(D25),gpio.get(D26),gpio.get(D27),gpio.get(D14)]
    #print(result)
    if max(result)==1: #Se c'è almeno un valore HIGH
        key=key_map[1][max_position(result)]
        gpio.set(D22,LOW)
        return(key)
    gpio.set(D22,LOW)

    gpio.set(D32,HIGH)
    result=[gpio.get(D25),gpio.get(D26),gpio.get(D27),gpio.get(D14)]
    #print(result)
    if max(result)==1: #Se c'è almeno un valore HIGH
        key=key_map[2][max_position(result)]
        #print(key)
        gpio.set(D32,LOW)
        return(key)
    gpio.set(D32,LOW)

    gpio.set(D33,HIGH)
    result=[gpio.get(D25),gpio.get(D26),gpio.get(D27),gpio.get(D14)]
    #print(result)
    if max(result)==1: #Se c'è almeno un valore HIGH
        key=key_map[3][max_position(result)]
        #print(key)
        gpio.set(D33,LOW)
        return(key)
    gpio.set(D33,LOW)
    return None