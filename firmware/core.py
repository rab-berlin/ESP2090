# Gemeinsame Grundlage fuer alle Teile der Firmware: Log, Ein-/Ausgaenge
# zum 2090, Web-Taster, Buzzer. Importiert nichts aus den anderen Teilen.
import uasyncio as asyncio
from machine import Pin, PWM
import machine, time

# Pinbelegung in hw.py (auch von boot.py benutzt)
from hw import out_1, out_2, out_3, out_4
from hw import GPIO_IN_REG, BUZZER_PIN

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
