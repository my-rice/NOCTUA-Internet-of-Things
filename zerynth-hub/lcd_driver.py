from bsp import board
import i2c
#L'indirizzo di default del display è 0x27 e il clock è 400000Hz

LCD_RS=0x01 #Maschera per il pin Register Set
LCD_RW=0x02 #Maschera per il pin Read/Write
LCD_EN=0x04 #Maschera per il pin Enable
LCD_BL=0x08 #Maschera per il pin BACKLIGHT

class LCD:
    def __init__(self,addr,backlight=True,displayon=True,cursoron=True,blinkingon=False):
        self._addr=addr
        self._port=i2c.I2c(addr,clock=400000)
        self._backlight=backlight
        self._lines=2
        self._displayon=displayon
        self._cursoron=cursoron
        self._blinkingon=blinkingon
        self.initialize()
    def _writeWithBacklight(self,PCFData):
        """
        La funzione prende in ingresso un byte e lo invia al PCF8574
        impostando il bit di backlight opportunamente in base al valore
        dell'attributo _backlight
        """
        if self._backlight:
            self._port.write(bytearray([PCFData | LCD_BL]))
            #print(hex(PCFData | LCD_BL))
        else:
            self._port.write(bytearray([PCFData & (~LCD_BL)]))
            #print(hex(PCFData & (~LCD_BL)))

    def _generateEnablePulse(self,PCFData):
        """
        La funzione prende in input un byte e lo invia al PCF8574 due volte
        impostando il bit EN prima a 1 e poi a 0. Ciò permette al display di 
        leggere correttamente l'istruzione a esso destinata. 
        Inoltre, il bit di backlight viene opportunamente impostatato.
        """
        self._writeWithBacklight(PCFData | LCD_EN)
        sleep(10,MICROS) #t_on=5us
        self._writeWithBacklight(PCFData & (~LCD_EN))
        sleep(50,MICROS) #t_off=50us
    def _execute4bitMode(self,LCDinstruction,dataRegister=False):
        """
        Scrive un'istruzione di 8 bit (D7-D0) come due istruzioni di 4 bit
        (D7-D4) per utilizzare l'LCD in modalità 4 bit. La funzione assume che
        l'operazione sia di scrittura (operazioni di lettura non supportate).
        Se dataRegister=True i dati sono scritti nella DDRAM o nella CGRAM.
        Per ogni istruzione il bit di backlight viene opportunamente impostatato.
        """
        highNible = LCDinstruction & 0xf0
        lowNible = (LCDinstruction << 4) & 0xf0
        if dataRegister:
            highNible |= LCD_RS
            lowNible |= LCD_RS
        self._generateEnablePulse(highNible)
        self._generateEnablePulse(lowNible)
    def _functionSet(self,interfaceBits=4,rows=2,font=0):
        """
        Fare riferimento all'istruzione "Function set" sul datasheet.
        Imposta modalità 4 bit, numero di righe e font del display.
        """
        instruction=0x20
        if interfaceBits == 8:
            instruction |= 0x10
        if rows>1:
            instruction |= 0x08
        if font == 1:
            instruction |= 0x04
        self._execute4bitMode(instruction)
    def _displaycontrol(self):
        """
        Esegue l'istruzione "Display Control" (fare riferimento al datasheet) in modalità
        4 bit. Tale funzione accende o spegne il display, imposta la presenza del cursore
        e l'eventuale blinking dello stesso sulla base del valore degli attributi _displayon
        _cursoron e _blinkingon.
        """
        instruction = 0x08
        if self._displayon:
            instruction |= 0x04
        if self._cursoron:
            instruction |= 0x02
        if self._blinkingon:
            instruction |= 0x01
        self._execute4bitMode(instruction)
    def _entrymodeset(self,moveDirection='increment',shift=0):
        """
        Esegue l'istruzione "Entry mode set" (fare riferimento al datasheet) in modalità
        4 bit. Tale funzione imposta la direzione di scorrimento e di shift sulla base del
        valore dei parametri moveDirection e shift.
        """
        instruction = 0x04
        if moveDirection == 'increment':
            instruction |= 0x02
        if shift == 1:
            instruction |= 0x01
        self._execute4bitMode(instruction)
    def _movecursor(self,direction='right'):
        """
        Permette di spostare il cursore a destra o a sinistra di una posizione.
        Fare riferimento all'istruzione "Cursor or display shift" sul datasheet.
        """
        instruction = 0x10
        if direction == 'right':
            instruction |= 0x04
        self._execute4bitMode(instruction)
    def _shiftdisplay(self,direction='right'):
        """
        Permette di shiftare il display a destra o a sinistra di una posizione.
        Fare riferimento all'istruzione "Cursor or display shift" sul datasheet.
        """
        instruction = 0x18
        if direction == 'right':
            instruction |= 0x04
        self._execute4bitMode(instruction)
    def _printcc(self,cc):
        """Stampa un carattere dato il suo Character Code"""
        self._execute4bitMode(cc,dataRegister=True)
    def _printchar(self,char):
        """Stampa un carattere ASCII. Ignora il resto dei caratteri"""
        char = char[0]
        cc = ord(char) #Estrai il codice ASCII del carattere
        if cc >= 32 and cc <= 125:
            self._printcc(cc) #Il character code coincide col codice ASCII per i caratteri compresi tra 32 e 125
    def _set_DDRAM_address(self,addr):
        """
        Imposta l'indirizzo della DDRAM (Display Data RAM) puntato dal cursore.
        """
        instruction = 0x80
        instruction |= addr
        #print("instruction in set_DDRAM_address",hex(instruction))
        self._execute4bitMode(instruction)

    def printstr(self,str):
        for c in str:
            self._printchar(c)
    def move_cursor(self,row,col): #TODO: Capire perchè non funziona! _write4bitmode mai testata per scrivere in DDRAM! Controlla sul datasheet se dev'essere un'operazione atomica! 
        if row > 1: row = 1
        if row < 0: row = 0
        if col < 0: col = 0
        if col > 39: col = 39
        if row == 0:
            addr = col
        elif row == 1:
            addr = 0x40+col
        #print("addr in move_cursor:",hex(addr))
        self._set_DDRAM_address(addr) #Imposta il cursore nella posizione addr
    def clear_and_print(self,str):
        """
        Funzione di utilità. Pulisce lo schermo e scrive la stringa andando
        automaticamente a capo alla fine della prima riga del display
        """
        self.clear()
        str1=str[0:16]
        str2=str[16:]
        self.printstr(str1)
        self.move_cursor(1, 0)
        self.printstr(str2)
    def enable_cursor(self):
        self._cursoron=True
        self._displaycontrol()
    def disable_cursor(self):
        self._cursoron=False
        self._displaycontrol()
    def enable_display(self):
        self._displayon=True
        self._displaycontrol()
    def disable_display(self):
        self._displayon=False
        self._displaycontrol()
    def enable_blinking(self):
        self._blinkingon=True
        self._displaycontrol()
    def disable_blinking(self):
        self._blinkingon=False
        self._displaycontrol()
    def clear(self):
        """
        Ripulisce il display e mette il cursore in posizione iniziale.
        Fare riferimento all'istruzione "Clear display" sul datasheet.
        """
        self._execute4bitMode(0x01)
        sleep(3) #prima era 1 ma non bastava! La clear richiede tempo! 3
    def initialize(self):
        sleep(40) #Software reset
        self._port.write(bytearray([0x3C]))
        sleep(5,MICROS)
        self._port.write(bytearray([0x38]))
        sleep(5)
        self._port.write(bytearray([0x3C]))
        sleep(5,MICROS)
        self._port.write(bytearray([0x38]))
        sleep(101,MICROS)
        self._port.write(bytearray([0x3C]))
        sleep(50,MICROS)
        self._port.write(bytearray([0x38]))
        sleep(50,MICROS)

        #print("generateEnablePulse")
        self._generateEnablePulse(0x20) #Imposta 4-bit mode, eseguita in 8-bit mode
        #print("functionSet")
        self._functionSet() #Imposta 4-bit mode, righe e font, eseguita in 4-bit mode
        #print("clear")
        self.clear()
        #print("displayControl")
        self._displaycontrol()
        #print("entryModeSet")
        self._entrymodeset()

    def greet(self):
        """Funzione di debug: scrive 'Hi!' sullo schemo"""
        sleep(5)
        self._port.write(bytearray([0x4D])) #write H
        sleep(50,MICROS)
        self._port.write(bytearray([0x49])) #w/ enable
        sleep(50,MICROS)
        self._port.write(bytearray([0x8D])) 
        sleep(50,MICROS)
        self._port.write(bytearray([0x89]))

        sleep(5)
        self._port.write(bytearray([0x6D])) #write I
        sleep(50,MICROS)
        self._port.write(bytearray([0x69])) #w/ enable
        sleep(50,MICROS)
        self._port.write(bytearray([0x9D])) 
        sleep(50,MICROS)
        self._port.write(bytearray([0x99]))

        sleep(5)
        self._port.write(bytearray([0x2D])) #write !
        sleep(50,MICROS)
        self._port.write(bytearray([0x29])) #w/ enable
        sleep(50,MICROS)
        self._port.write(bytearray([0x1D])) 
        sleep(50,MICROS)
        self._port.write(bytearray([0x19]))
    def continuous_writing(self,str):
        """Funzione sperimentale"""
        i=0
        self.clear()
        while i<40:
            self.move_cursor(0, i)
            self.printstr(str)
            i=i+3
            self.move_cursor(1, i)
            i=i+len(str)
        while True:
            self._shiftdisplay(direction='left')
            sleep(300)

print("[SYS] JANUS loaded")