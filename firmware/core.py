# Gemeinsame Grundlage fuer alle Teile der Firmware: Log, Ein-/Ausgaenge
# zum 2090, Web-Taster, Buzzer, LED-Puffer. Importiert nichts aus den anderen Teilen.
import uasyncio as asyncio
from machine import Pin, PWM
import machine, time
import neopixel

# Pinbelegung in hw.py (auch von boot.py benutzt)
from hw import out_1, out_2, out_3, out_4
from hw import GPIO_IN_REG, BUZZER_PIN, LED_PIN

# ================= LOG =================
# Nur im RAM fuer die Weboberflaeche (/status), keine Log-Dateien im Flash.
LOG_SIZE = 40
log_buffer = []
log_version = 0

def log(msg):
    global log_version
    log_version += 1
    msg = str(msg)[:100]
    log_buffer.append(msg)
    if len(log_buffer) > LOG_SIZE:
        log_buffer.pop(0)

def exception_text(e):
    """Fehlerart und Text, z. B. "NameError: name 'x' isn't defined"."""
    text = str(e)
    return type(e).__name__ + (": " + text if text else "")

# ================= LED-PUFFER =================
ROWS = 8
COLS = 8

# ----- Helligkeit begrenzen (Versorgung ueber USB) -----
# Jede LED zieht je Farbkanal bei 255 etwa 20 mA. Ueber LED_MAX_MA wird das
# ganze Bild beim Schreiben gleichmaessig dunkler; die gesetzten Werte bleiben.
# Am PC-Port (500 mA) nicht erhoehen; mit eigenem Netzteil (>= 2 A) bis ca. 1000.
LED_MAX_MA = 250
LED_BUDGET = LED_MAX_MA * 255 // 20     # Summe aller Farbwerte (r+g+b ueber alle LEDs)

# ----- Ausrichtung -----
# Die Matrix kann in 4 Lagen eingebaut sein. Gezeichnet wird immer im aufrechten
# Bild (np[x * 8 + y], x = 0 links, y = 0 unten); erst write() dreht es um
# ROTATIONS Grad im Uhrzeigersinn auf die LEDs. Die Vorschau im Browser (hex_rows)
# und np[i] in User-Scripts bleiben aufrecht. Einstellung: Weboberflaeche (/rotation).
ROTATIONS = (0, 90, 180, 270)

def rotation_map(deg):
    """Fuer jedes Pixel x * 8 + y des aufrechten Bildes die LED-Nummer (None bei 0 Grad)."""
    if deg == 0:
        return None
    m = []
    for x in range(COLS):
        for y in range(ROWS):
            if deg == 90:
                x2, y2 = y, COLS - 1 - x
            elif deg == 180:
                x2, y2 = COLS - 1 - x, ROWS - 1 - y
            else:
                x2, y2 = ROWS - 1 - y, x
            m.append(x2 * ROWS + y2)
    return m

class LimitedPixels:
    """Wie neopixel.NeoPixel, aber write() haelt LED_MAX_MA ein und dreht das Bild
    (fuer Matrix und User-Scripts)."""

    def __init__(self, pixels):
        self._np = pixels
        self.n = len(pixels)
        self.version = 0                      # zaehlt jedes write() (Anzeige im Browser)
        self.rotation = 0
        self._map = None

    def set_rotation(self, deg):
        """0, 90, 180 oder 270 (Grad im Uhrzeigersinn); gilt ab dem naechsten write()."""
        if deg not in ROTATIONS:
            return False
        self.rotation = deg
        self._map = rotation_map(deg)
        return True

    def __len__(self):
        return self.n

    def __setitem__(self, i, color):
        self._np[i] = color

    def __getitem__(self, i):
        return self._np[i]

    def fill(self, color):
        self._np.fill(color)

    def hex_rows(self):
        """64 Farben als "rrggbb", oberste Zeile zuerst, je Zeile links nach rechts
        (Verdrahtung np[x * 8 + y], y = 0 unten)."""
        px = self._np
        out = []
        for y in range(ROWS - 1, -1, -1):
            for x in range(COLS):
                c = px[x * ROWS + y]
                out.append("%02x%02x%02x" % (c[0], c[1], c[2]))
        return "".join(out)

    def write(self):
        self.version += 1
        px, n = self._np, self.n
        total = 0
        for i in range(n):
            c = px[i]
            total += c[0] + c[1] + c[2]
        m = self._map
        if total <= LED_BUDGET and m is None:
            px.write()
            return
        k = min(256, LED_BUDGET * 256 // total) if total else 256    # Faktor * 256
        saved = [px[i] for i in range(n)]
        for i in range(n):
            c = saved[i]
            px[m[i] if m else i] = ((c[0] * k) >> 8, (c[1] * k) >> 8, (c[2] * k) >> 8)
        px.write()
        for i in range(n):
            px[i] = saved[i]                  # gesetzte Werte wiederherstellen

np = LimitedPixels(neopixel.NeoPixel(Pin(LED_PIN), ROWS * COLS))

# ================= GPIO =================
# ----- Web-Taster -----
tasteG = {"pressed": False}
tasteH = {"pressed": False}

def setOutputs(value):
    out_1.value(value & 1)
    value >>= 1
    out_2.value(value & 1)
    value >>= 1
    out_3.value(value & 1)
    value >>= 1
    out_4.value(value & 1)
    
# Der 2090 schaltet seine Ausgaenge bei DOT nacheinander (ca. 140-170 us).
# getInputs() liest alle vier in einem Zugriff und so lange erneut, bis zwei
# Lesungen im Abstand von INPUT_SETTLE_US gleich sind - also nie einen Zwischenwert.
INPUT_SETTLE_US = 200

def getInputs():
    v = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111
    while True:
        time.sleep_us(INPUT_SETTLE_US)
        w = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111
        if w == v:
            return v
        v = w

async def waitInputs(value=None, timeout_ms=None):
    """Warten, bis die Ausgaenge des 2090 den Wert `value` zeigen (ohne value:
    bis sich der Wert aendert). Gibt den Wert zurueck, bei Timeout None."""
    start = time.ticks_ms()
    old = getInputs()
    while True:
        v = getInputs()
        if (v == value) if value is not None else (v != old):
            return v
        if timeout_ms is not None and time.ticks_diff(time.ticks_ms(), start) >= timeout_ms:
            return None
        await asyncio.sleep_ms(5)

# ================= BUZZER =================

buzzer_pwm = PWM(Pin(BUZZER_PIN))
buzzer_pwm.duty_u16(0)

beep_queue = []
BEEP_QUEUE_MAX = 32     # mehr Toene warten nicht; weitere beep() werden ignoriert

def beep(freq, duration_ms=None):
    if len(beep_queue) < BEEP_QUEUE_MAX:
        beep_queue.append((freq, duration_ms))

def stop_sound():
    beep_queue.clear()
    buzzer_pwm.duty_u16(0)

async def buzzer_play_task():
    while True:
        if beep_queue:
            freq, dur = beep_queue.pop(0)

            if freq > 0:
                buzzer_pwm.freq(freq)
                buzzer_pwm.duty_u16(20000)
            else:
                buzzer_pwm.duty_u16(0)

            # Dauerhafter Ton
            if dur is None:
                # Warten bis neuer Eintrag kommt
                while not beep_queue:
                    await asyncio.sleep_ms(10)
                # danach direkt naechsten Eintrag verarbeiten
                continue

            # Zeitgesteuerter Ton
            await asyncio.sleep_ms(dur)
            buzzer_pwm.duty_u16(0)

        else:
            await asyncio.sleep_ms(10)
