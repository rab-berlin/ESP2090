# LED-Matrix: Strombegrenzung, Lese-Task (zeitkritisch), Schlafen/Wecken,
# Start/Stop/Loeschen, Farben aus Userscripts.
import uasyncio as asyncio
from machine import Pin
import machine, time, sys
import neopixel

from hw import out_1, GPIO_IN_REG, LED_PIN
from core import log, exception_text

# ================= LED MATRIX =================
# Matrix-Protokoll v2 (siehe Matrix-Protokoll.md):
#   REQ (out_1) -> 2090 gibt ACK (1-15) auf Ausg1-4 aus -> Datennibbles.
#   ACK 1:     ein Befehl Pause (EXRL/EXRM), dann 16 Nibbles Schritt fuer Schritt
#   ACK 2-15:  die Nibbles folgen direkt im naechsten Schritt
# Die Zeichenlogik steht in matrix_draw.py.

import matrix_draw

matrix_tasks_running = False
matrix_asleep = False        # ACK 15: Schlafmodus, REQ bleibt Low bis F auf den Ausgaengen
wake_released = False        # Schlaf: die Ausgaenge haben das F des ACK 15 verlassen
after_wake = False           # gerade geweckt: das naechste REQ steht bis zu WAKE_REQ_US
wake_prev = 0                # Schlaf: letzter gesehener Wert der Ausgaenge (15 = altes F, weckt nicht)
CONSOLE_MATRIX = False       # Bild nach jedem Neuaufbau auf die Konsole (/status?con=1 schaltet ein; bremst)

ROWS = 8
COLS = 8
NUM_LEDS = ROWS * COLS

# Timing-Parameter (us)
WAIT_AFTER_DETECT = 700      # nach der ersten Flanke, bis die Ausgaenge stabil sind
WAIT_AFTER_REQ = 30000       # Timeout fuer das ACK
WAIT_GUARD = 40000           # nach dem Timeout: REQ ist Low, ein schon begonnenes ACK noch abwarten
IDLE_SLEEP_MS = 20           # danach abgeben (Weboberflaeche, LED Stop), REQ bleibt Low
WAIT_AFTER_1 = 13500         # ACK 1: erstes Nibble wird WAIT_AFTER_1 + NIBBLE_INTERVAL nach ack_time gelesen
WAIT_AFTER_ACK = 13500       # ACK 2-15: erstes Nibble wird WAIT_AFTER_ACK nach ack_time gelesen
NIBBLE_INTERVAL = 9217
NUM_NIBBLES = 16
SLEEP_ACK = 15               # ACK 15: schlafen (ohne Nibble)
WAKE_POLL_MS = 1             # im Schlaf: Ausgaenge so oft lesen (der 2090 haelt das F, bis REQ kommt)
SLEEP_RELEASE_US = 40000     # nach ACK 15 so lange warten, bis der 2090 das F wieder wegnimmt;
                             # steht es laenger, ist es ein Wecksignal (der ESP bleibt wach)
WAKE_REQ_US = 200000         # erstes REQ nach dem Wecken: so lange auf das ACK warten

# ----- Helligkeit begrenzen (Versorgung ueber USB) -----
# Jede LED zieht je Farbkanal bei 255 etwa 20 mA. Ueber LED_MAX_MA wird das
# ganze Bild beim Schreiben gleichmaessig dunkler; die gesetzten Werte bleiben.
# Am PC-Port (500 mA) nicht erhoehen; mit eigenem Netzteil (>= 2 A) bis ca. 1000.
LED_MAX_MA = 250
LED_BUDGET = LED_MAX_MA * 255 // 20     # Summe aller Farbwerte (r+g+b ueber alle LEDs)

class LimitedPixels:
    """Wie neopixel.NeoPixel, aber write() haelt LED_MAX_MA ein (fuer Matrix und User-Scripts)."""

    def __init__(self, pixels):
        self._np = pixels
        self.n = len(pixels)
        self.version = 0                      # zaehlt jedes write() (Anzeige im Browser)

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
        if total <= LED_BUDGET:
            px.write()
            return
        k = LED_BUDGET * 256 // total       # Faktor * 256
        saved = [px[i] for i in range(n)]
        for i in range(n):
            c = saved[i]
            px[i] = ((c[0] * k) >> 8, (c[1] * k) >> 8, (c[2] * k) >> 8)
        px.write()
        for i in range(n):
            px[i] = saved[i]                  # gesetzte Werte wiederherstellen

np = LimitedPixels(neopixel.NeoPixel(Pin(LED_PIN), NUM_LEDS))

M = matrix_draw.Matrix()     # Bitebene, Farbebene, Cursor, Farbe, Stapel
matrix_dirty = True # initial


def start_matrix_tasks():
    global matrix_display_task_handle, matrix_task_handle, matrix_tasks_running, matrix_asleep

    if matrix_tasks_running:
        log("LED task already running")
        return
    
    log("LED task started")
    matrix_asleep = False
    matrix_display_task_handle = asyncio.create_task(matrix_display_task())
    matrix_task_handle = asyncio.create_task(matrix_task_guarded())
    matrix_tasks_running = True
    

async def matrix_task_guarded():
    # Bricht matrix_task mit einem Fehler ab, soll die Oberflaeche nicht weiter
    # "LED on" zeigen: Fehler ins Log, Anzeige-Task beenden, Zustand zuruecksetzen.
    # matrix_task selbst bleibt unveraendert (zeitkritisch).
    global matrix_display_task_handle, matrix_task_handle, matrix_tasks_running, matrix_asleep
    try:
        await matrix_task()
    except asyncio.CancelledError:
        raise
    except Exception as e:
        out_1.value(0)   # REQ Low
        if matrix_display_task_handle:
            matrix_display_task_handle.cancel()
            matrix_display_task_handle = None
        matrix_task_handle = None
        matrix_tasks_running = False
        matrix_asleep = False
        log("LED task error: {} - matrix stopped".format(exception_text(e)))


def stop_matrix_tasks():
    global matrix_display_task_handle, matrix_task_handle, matrix_tasks_running, matrix_asleep

    if not matrix_tasks_running:
        log("Matrix already stopped")
        return

    if matrix_display_task_handle:
        matrix_display_task_handle.cancel()
        matrix_display_task_handle = None

    if matrix_task_handle:
        matrix_task_handle.cancel()
        matrix_task_handle = None
    out_1.value(0)   # REQ Low

    matrix_tasks_running = False
    matrix_asleep = False
    matrix_clear()
    log("LED task stopped")


def matrix_clear():
    # LED off: Bitmatrix, Farbmatrix, Stapel, Cursor und aktive Farbe zuruecksetzen
    # (Palette bleibt) und die Anzeige sofort dunkel schalten. "LED on" loescht nicht,
    # damit Farben aus einem Userscript (setColors) erhalten bleiben.
    global matrix_dirty
    M.clear()
    matrix_dirty = True
    matrix_show()


def setColors(user_colors):
    """Fuer User-Scripts: 64 Farbnamen, oberste Zeile zuerst."""
    if not M.set_colors(user_colors):
        log("Error: color matrix must be 8x8")

def setPalette(index, rgb):
    """Fuer User-Scripts: Farbe 0-15 der Palette aendern, z. B. setPalette(10, (5, 0, 5))."""
    global matrix_dirty
    if M.set_palette(index, rgb):
        matrix_dirty = True
    else:
        log("Error: palette has colors 0-15")
   

def matrix_show():
    """Anzeige neu aufbauen, wenn sich etwas geaendert hat."""
    global matrix_dirty
    if matrix_dirty:
        matrix_dirty = False
        M.render(np)
        np.write()
        if CONSOLE_MATRIX:
            matrix_print_console(M.bits)


async def matrix_display_task():
    # matrix_task zeigt empfangene Bilder sofort selbst an (matrix_show); hier kommen
    # nur noch Aenderungen von aussen an (User-Scripts: setColors, setPalette).
    while True:
        matrix_show()
        await asyncio.sleep_ms(20)


def matrix_print_console(matrix):
    sys.stdout.write("\x1b[2J")
    sys.stdout.write("\x1b[H")

    for r in reversed(range(ROWS)):  # Zeilen von oben nach unten
        line = ""
        for c in range(COLS):
            idx = r * COLS + c
            line += "*" if matrix[idx] else " "
            line += " "
        print(line)
    print()
    

def matrix_go_sleep():
    """Direkt nach dem ACK 15 (noch blockierend): warten, bis der 2090 das F des ACK 15
    wegnimmt (bei der ueblichen Routine 2 Schritte, ca. 19 ms). Ab dann weckt jedes F,
    das die Abfrage sieht."""
    global wake_released
    t0 = time.ticks_us()
    while (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111 == 15:
        if time.ticks_diff(time.ticks_us(), t0) >= SLEEP_RELEASE_US:
            break
    wake_released = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111 != 15
    global after_wake
    if not wake_released:
        # Das F steht laenger als ein ACK 15 (2 Schritte): Der 2090 haelt es als Wecksignal
        # und wartet auf REQ (z. B. weil der ESP noch wach war). Nicht schlafen, gleich REQ.
        after_wake = True
        return
    matrix_sleep_now(0)


def matrix_sleep_now(last):
    """Einschlafen. last = Wert, der gerade auf den Ausgaengen liegt: Ist es F (letztes
    Datennibble), weckt erst ein neuer Wechsel auf F."""
    global matrix_asleep, wake_prev
    wake_prev = 15 if last == 15 else 0
    matrix_asleep = True


async def matrix_wait_wake():
    """Schlaf: REQ bleibt Low, der 2090 kann Eingang 1 und die Ausgaenge frei benutzen
    (Taster, Keypad). Geweckt wird mit F auf den Ausgaengen, das 0,7 ms spaeter noch
    anliegt. Der 2090 haelt das F, bis er REQ sieht; wie spaet diese Abfrage drankommt
    (Weboberflaeche), spielt deshalb keine Rolle. Ein F, das schon beim Einschlafen
    anlag (wake_prev), weckt nicht."""
    global matrix_asleep, after_wake
    prev = wake_prev
    while True:
        v = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111
        if v == 15 and prev != 15:
            time.sleep_us(WAIT_AFTER_DETECT)
            if (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111 == 15:
                break
        prev = v
        await asyncio.sleep_ms(WAKE_POLL_MS)
    after_wake = True
    matrix_asleep = False


async def matrix_task():
    
    global matrix_dirty, matrix_asleep, after_wake
    nibbles_of = matrix_draw.NIBBLES

    while True:

        # Schlafmodus (ACK 15): kein REQ, bis der 2090 mit F weckt.
        # Danach sofort REQ; ein ACK gilt wie immer erst nach einer 0.
        if matrix_asleep:
            await matrix_wait_wake()
            continue
        
        # =========================
        # 1. REQ setzen
        # =========================
        out_1.value(1)  # REQ = HIGH
        req_time = time.ticks_us()
        ack_time = None
        seen_zero = False
        saw_f = False                                  # F liegt an (gehaltenes Wecksignal)
        auto_sleep = False                             # ACK kam direkt aus dem gehaltenen F: danach schlafen
        last = 0                                       # zuletzt gelesenes Nibble
        timed_out = False
        req_len = WAKE_REQ_US if after_wake else WAIT_AFTER_REQ
        after_wake = False

        # =========================
        # 2. Auf ACK warten 
        # =========================
        while True:
            
            # hier asyncio sleep, aber funktioniert nicht...
                        
            now = time.ticks_us()
            elapsed = time.ticks_diff(now, req_time)
            
            ack = 0
            v = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111

            if not seen_zero:
                if v == 0:
                    seen_zero = True                               # erst Ruhe (0), dann gilt eine Flanke als ACK
                elif v == 15:
                    saw_f = True                                   # der 2090 haelt F, bis er REQ sieht
                elif saw_f:                                        # F weggenommen: zaehlt wie eine 0,
                    time.sleep_us(WAIT_AFTER_DETECT)               # der neue Wert kann schon das ACK sein
                    ack = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111
                    if ack == 0:
                        seen_zero = True
                    elif ack != 15:
                        ack_time = time.ticks_us()
                        out_1.value(0)
                        auto_sleep = True
                        break
            elif v:                                                # Irgendwas hat "gezuckt"
                time.sleep_us(WAIT_AFTER_DETECT)                   # bremst, damit Ausgaenge stabil sind
                ack = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111   # liest nochmal ein
                ack_time = time.ticks_us()
                out_1.value(0)  # REQ sofort LOW
                break
            
            # Timeout: REQ Low. Hat der 2090 REQ kurz vorher noch gesehen, kommt
            # sein ACK bis zu 3 Schritte spaeter; so lange wird weiter gelesen.
            if not timed_out and elapsed >= req_len:
                out_1.value(0)
                timed_out = True
            elif timed_out and elapsed >= req_len + WAIT_GUARD:
                break

        if ack_time is None:
            # Kein ACK: REQ ist Low, der 2090 kann jetzt nicht beginnen.
            # Abgeben ist hier sicher (Weboberflaeche, LED Stop, auch wenn die
            # Ausgaenge dauerhaft belegt sind, z. B. waehrend Reset am 2090).
            await asyncio.sleep_ms(IDLE_SLEEP_MS)
            continue # zum Schleifenanfang
        
        if ack == 1:
            start_time = time.ticks_add(ack_time, WAIT_AFTER_1)
            while time.ticks_diff(start_time, time.ticks_us()) > 0:
                pass
      
            next_time = time.ticks_add(start_time, NIBBLE_INTERVAL)
            idx = 0
            matrix = M.bits
        
            for _ in range(NUM_NIBBLES):
                
                while time.ticks_diff(next_time, time.ticks_us()) > 0:
                    pass
                
                v = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111

                matrix[idx]     = v & 1
                matrix[idx + 1] = (v >> 1) & 1
                matrix[idx + 2] = (v >> 2) & 1
                matrix[idx + 3] = (v >> 3) & 1
                idx += 4
                
                next_time = time.ticks_add(next_time, NIBBLE_INTERVAL)
            
            last = v
            matrix_dirty = True

        elif ack == SLEEP_ACK:
            matrix_go_sleep()

        elif nibbles_of[ack]:
            # ACK 2-15: Nibbles direkt im naechsten Schritt, gelesen in dessen Mitte
            n = nibbles_of[ack]
            data = [0] * n
            next_time = time.ticks_add(ack_time, WAIT_AFTER_ACK)
            for k in range(n):
                while time.ticks_diff(next_time, time.ticks_us()) > 0:
                    pass
                data[k] = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111
                next_time = time.ticks_add(next_time, NIBBLE_INTERVAL)
            last = data[n - 1]
            try:
                if M.command(ack, data):
                    matrix_dirty = True
            except Exception as e:
                log("Matrix command {} {}: {}".format(ack, data, e))

        # Kam das ACK direkt aus einem gehaltenen F (Wecken fuer genau einen Befehl),
        # schlaeft der ESP danach von selbst wieder: kein REQ, bis das naechste F weckt.
        if auto_sleep and not matrix_asleep and not after_wake:
            matrix_sleep_now(last)

        matrix_show()                                  # Bild sofort anzeigen
            
        await asyncio.sleep_ms(10) # fuer display task
