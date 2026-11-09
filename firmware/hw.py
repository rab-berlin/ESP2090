# Pinbelegung der Erweiterung (gemeinsam fuer boot.py und main.py)
#
# Signalwege siehe docs/Analyse-Code-und-Schaltplan.md, Abschnitt 1.
from machine import Pin

# Ausgaenge ESP -> Eingaenge des 2090 (Eing1-4, ODER mit den Klemmen Eing1K-4K)
out_1 = Pin(20, Pin.OUT)
out_2 = Pin(21, Pin.OUT)
out_3 = Pin(4, Pin.OUT)
out_4 = Pin(3, Pin.OUT)

# Eingaenge ESP <- Ausgaenge des 2090 (Ausg1-4)
in_1 = Pin(5, Pin.IN, Pin.PULL_DOWN)
in_2 = Pin(6, Pin.IN, Pin.PULL_DOWN)
in_3 = Pin(7, Pin.IN, Pin.PULL_DOWN)
in_4 = Pin(8, Pin.IN, Pin.PULL_DOWN)

OUTPUTS = [out_1, out_2, out_3, out_4]
INPUTS = [in_1, in_2, in_3, in_4]

# GPIO-Eingangsregister des ESP32-C3: (Wert >> 5) & 0xF = in_1 .. in_4 in einem Zugriff
GPIO_IN_REG = 0x6000403C

LED_PIN = 2        # Daten der LED-Matrix (WS2812, 8 x 8)
BUZZER_PIN = 10    # passiver Piezo
