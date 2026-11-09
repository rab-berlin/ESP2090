import uasyncio as asyncio
from microdot import Microdot, Response
from machine import Pin, PWM
import machine, network, gc, time, os, json
import neopixel
import sys

# ================= GPIO =================
# Pinbelegung in hw.py (auch von boot.py benutzt)
from hw import out_1, out_2, out_3, out_4, in_1, in_2, in_3, in_4
from hw import INPUTS, GPIO_IN_REG, LED_PIN, BUZZER_PIN

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
    
def getInputs():
    value = 0
    for i, pin in enumerate (INPUTS):
        bit = pin.value() & 1
        value |= bit << i
    return value

# ================= LED MATRIX =================
# Matrix-Protokoll v2 (siehe Matrix-Protokoll.md):
#   REQ (out_1) -> 2090 gibt ACK (1-15) auf Ausg1-4 aus -> Datennibbles.
#   ACK 1:     ein Befehl Pause (EXRL/EXRM), dann 16 Nibbles Schritt fuer Schritt
#   ACK 2-15:  die Nibbles folgen direkt im naechsten Schritt
# Die Zeichenlogik steht in matrix_draw.py.

import matrix_draw

matrix_tasks_running = False
matrix_display_task_handle = None
matrix_task_handle = None

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

M = matrix_draw.Matrix()     # Bitebene, Farbebene, Cursor, Farbe, Anzeige an/aus
matrix_dirty = True # initial


def start_matrix_tasks():
    global matrix_display_task_handle, matrix_task_handle, matrix_tasks_running

    if matrix_tasks_running:
        log("LED task already running")
        return
    
    log("LED task started")
    matrix_display_task_handle = asyncio.create_task(matrix_display_task())
    matrix_task_handle = asyncio.create_task(matrix_task())
    matrix_tasks_running = True
    

def stop_matrix_tasks():
    global matrix_display_task_handle, matrix_task_handle, matrix_tasks_running

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
    log("LED task stopped")


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
   

async def matrix_display_task():
    global matrix_dirty

    while True:

        if matrix_dirty:
            matrix_dirty = False
            M.render(np)
            np.write()
            matrix_print_console(M.bits)
            
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
    

async def matrix_task():
    
    global matrix_dirty
    nibbles_of = matrix_draw.NIBBLES

    while True:
        
        # =========================
        # 1. REQ setzen
        # =========================
        out_1.value(1)  # REQ = HIGH
        req_time = time.ticks_us()
        ack_time = None
        seen_zero = False
        timed_out = False

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
            elif v:                                                # Irgendwas hat "gezuckt"
                time.sleep_us(WAIT_AFTER_DETECT)                   # bremst, damit Ausgaenge stabil sind
                ack = (machine.mem32[GPIO_IN_REG] >> 5) & 0b1111   # liest nochmal ein
                ack_time = time.ticks_us()
                out_1.value(0)  # REQ sofort LOW
                break
            
            # Timeout: REQ Low. Hat der 2090 REQ kurz vorher noch gesehen, kommt
            # sein ACK bis zu 3 Schritte spaeter; so lange wird weiter gelesen.
            if not timed_out and elapsed >= WAIT_AFTER_REQ:
                out_1.value(0)
                timed_out = True
            elif timed_out and elapsed >= WAIT_AFTER_REQ + WAIT_GUARD:
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
            
            matrix_dirty = True

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
            try:
                if M.command(ack, data):
                    matrix_dirty = True
            except Exception as e:
                log("Matrix command {} {}: {}".format(ack, data, e))
            
        await asyncio.sleep_ms(10) # fuer display task

                
        
# ================= SERVER =================
app = Microdot()
current_task = None
LOG_SIZE = 40
log_buffer = []

# ================= LOG =================
# Nur im RAM fuer die Weboberflaeche (/status), keine Log-Dateien im Flash.

log_version = 0

def log(msg):
    global log_version
    log_version += 1
    msg = str(msg)[:100]
    log_buffer.append(msg)
    if len(log_buffer) > LOG_SIZE:
        log_buffer.pop(0)

# ================= SCRIPT-PRUEFUNG =================
# Vor dem Start (und als Warnung beim Speichern): Scripts laufen als Task im
# selben Event-Loop wie Webserver und Matrix. Eine Schleife ohne await haelt
# alles an und laesst sich nicht stoppen. Regeln:
#   - jede while-/for-Schleife braucht ein await im Rumpf;
#     ausgenommen for ... in range(n) mit fester Zahl n <= FOR_RANGE_MAX
#   - kein time.sleep / sleep_ms / sleep_us (blockiert), kein input()
# Grenze: geprueft wird, ob ein await im Rumpf steht, nicht ob es ausgefuehrt wird.
FOR_RANGE_MAX = 64

def _code_lines(code):
    """Zeilen ohne Kommentare und ohne Inhalt von Zeichenketten (Zeilen bleiben gleich)."""
    out, cur = [], []
    i, n = 0, len(code)
    quote = None                     # aktuelles Anfuehrungszeichen (' " \'\'\' \"\"\")
    while i < n:
        c = code[i]
        if quote:
            if c == "\\":
                if code[i + 1:i + 2] == "\n":      # Zeilenfortsetzung in der Zeichenkette
                    out.append("".join(cur))
                    cur = []
                i += 2
                continue
            if code.startswith(quote, i):
                cur.append(quote)
                i += len(quote)
                quote = None
                continue
            if c == "\n":
                out.append("".join(cur))
                cur = []
            i += 1
            continue
        if c == "#":
            while i < n and code[i] != "\n":
                i += 1
            continue
        if c in "'\"":
            quote = c * 3 if code.startswith(c * 3, i) else c
            cur.append(quote)
            i += len(quote)
            continue
        if c == "\n":
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out

def _is_name_char(c):
    return c.isalpha() or c.isdigit() or c == "_"

def _find_word(s, w, start=0):
    """Position von w als ganzes Wort in s, sonst -1."""
    i = s.find(w, start)
    while i >= 0:
        before = s[i - 1] if i > 0 else " "
        after = s[i + len(w)] if i + len(w) < len(s) else " "
        if not _is_name_char(before) and not _is_name_char(after):
            return i
        i = s.find(w, i + 1)
    return -1

def _indent(line):
    return len(line) - len(line.lstrip())

def _small_range(header):
    """True bei 'for x in range(...)' mit festen Zahlen und hoechstens FOR_RANGE_MAX Durchlaeufen."""
    i = header.find(" in ")
    if i < 0:
        return False
    rest = header[i + 4:].strip()
    if not rest.startswith("range(") or rest.find(")") < 0:
        return False
    args = rest[6:rest.find(")")]
    try:
        nums = [int(a) for a in args.split(",")]
        if not 1 <= len(nums) <= 3:
            return False
        return len(range(*nums)) <= FOR_RANGE_MAX
    except Exception:
        return False

def _header_colon(text):
    """Position des Doppelpunkts, der den Schleifenkopf beendet (ausserhalb von Klammern)."""
    depth = 0
    for i, c in enumerate(text):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and depth == 0:
            return i
    return -1

def script_problem(code):
    """Erstes Problem als Text ("line N: ..."), sonst None."""
    lines = _code_lines(code)
    for no, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        for mod in ("time.", "utime."):
            p = text.find(mod + "sleep")
            if p >= 0 and (p == 0 or not _is_name_char(text[p - 1])):
                return "line {}: time.sleep blocks everything - use await asyncio.sleep_ms(...)".format(no + 1)
        if _find_word(text, "input") >= 0 and text[_find_word(text, "input") + 5:].lstrip().startswith("("):
            return "line {}: input() is not available".format(no + 1)

        kind = None
        if text.startswith("while") and not _is_name_char(text[5:6] or " "):
            kind = "while"
        elif text.startswith("for") and not _is_name_char(text[3:4] or " "):
            kind = "for"
        if not kind:
            continue
        colon = _header_colon(text)
        if colon < 0:
            continue        # kein Schleifenkopf, z. B. "for" in einem mehrzeiligen Listen-Ausdruck
        header = text[:colon]
        if kind == "for" and _small_range(header):
            continue
        # Rumpf: Rest der Zeile nach dem Doppelpunkt + alle tiefer eingerueckten Zeilen
        body = [text[colon + 1:]]
        ind = _indent(line)
        for nxt in lines[no + 1:]:
            if not nxt.strip():
                continue
            if _indent(nxt) <= ind:
                break
            body.append(nxt)
        if not any(_find_word(b, "await") >= 0 for b in body):
            what = "while loop" if kind == "while" else \
                "for loop (more than {} passes or not a fixed range)".format(FOR_RANGE_MAX)
            return "line {}: {} without await - add e.g. await asyncio.sleep_ms(20)".format(no + 1, what)
    return None

# ================= USER SCRIPT =================

def indent(txt,n):
    return "\n".join(" "*n + line for line in txt.split("\n"))

async def run_user_script(code):
    global current_task

    try:

        wrapped=f"""
import uasyncio as asyncio
async def __user_task():
{indent(code,4)}
"""

        ns={
            "out_1":out_1,"out_2":out_2,"out_3":out_3,"out_4":out_4,
            "in_1":in_1,"in_2":in_2,"in_3":in_3,"in_4":in_4,
            "setOutputs":setOutputs,
            "getInputs": getInputs,
            "tasteG":tasteG,
            "tasteH":tasteH,
            "log":log,
            "beep":beep,
            "setColors":setColors,
            "setPalette":setPalette,
            "np":np
        }

        exec(wrapped,ns)

        current_task=asyncio.create_task(ns["__user_task"]())
        log("User script started")

        await current_task

    except asyncio.CancelledError:
        log("User script stopped")

    except Exception as e:
        log("ERROR "+str(e))

    setOutputs(0)   # auch nach normalem Ende oder Fehler
    gc.collect()

# ================= BUSCH UPLOAD =================

delay_bit_us = 10000
delay_after_value_us = 10000

def clock_signal(pin, delay_us):
    pin.value(1)
    time.sleep_us(delay_us // 2)
    pin.value(0)
    time.sleep_us(delay_us // 2)

def load_instruction_to_busch2090(instr):

    for y in range(3):

        mask = 1

        for z in range(4):

            out_1.value(1 if (int(instr[y], 16) & mask) else 0)

            if y == 0 and z == 0:
                out_3.value(1)
                time.sleep_us(delay_bit_us)
            else:
                clock_signal(out_2, delay_bit_us)

            mask <<= 1

    setOutputs(0)
    time.sleep_us(delay_after_value_us)

def is_valid(instr):
    return len(instr) == 3 and all(c in "0123456789ABCDEF" for c in instr)

MIC_MAX_STEPS = 256     # Programmspeicher des 2090

def mic_instructions(text):
    """Befehle aus dem Text einer .mic-Datei: erste 3 Zeichen jeder Zeile,
    I/L -> 1, O/Q -> 0, nur gueltige Hex-Befehle. Gleiche Regeln wie
    micInstructions() in index.html."""
    if text.startswith("\ufeff"):
        text = text[1:]                                   # BOM
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip().upper()
        if len(line) < 3:
            continue
        instr = (line[0:3]
            .replace("I", "1")
            .replace("L", "1")
            .replace("O", "0")
            .replace("Q", "0"))
        if is_valid(instr):
            out.append(instr)
    return out

def multipart_file(body, content_type, field="file"):
    """Inhalt des Formularfelds `field` aus multipart/form-data, sonst None."""
    i = content_type.find("boundary=")
    if i < 0:
        return None
    boundary = content_type[i + 9:].split(";")[0].strip().strip('"')
    if not boundary:
        return None
    marker = b'; name="' + field.encode() + b'"'
    for part in body.split(b"--" + boundary.encode()):
        head_end = part.find(b"\r\n\r\n")
        if head_end < 0 or marker not in part[:head_end]:
            continue
        data = part[head_end + 4:]
        if data.endswith(b"\r\n"):
            data = data[:-2]                              # Zeilenende vor der naechsten Grenze
        return data
    return None

def send_busch_instructions(instructions):
    log("MIC upload started ({} instructions)".format(len(instructions)))
    try:
        for instr in instructions:
            load_instruction_to_busch2090(instr)
    except Exception as e:
        log("MIC upload error: " + str(e))
    setOutputs(0)
    log("MIC upload finished")

@app.post('/busch_upload')
async def busch_upload(req):
    # Formular aus dem Browser (multipart/form-data, Feld "file") oder die Datei
    # direkt als Body (z. B. curl --data-binary @prog.mic -H "Content-Type: text/plain").
    ctype = req.headers.get("Content-Type", "")
    body = req.body or b""
    if ctype.startswith("multipart/form-data"):
        data = multipart_file(body, ctype)
        if data is None:
            return "No MIC file in upload", 400
    else:
        data = body

    try:
        text = data.decode()
    except UnicodeError:
        return "MIC file is not a text file", 400

    instr = mic_instructions(text)
    if not instr:
        return "No valid instructions in MIC file", 400
    if len(instr) > MIC_MAX_STEPS:
        return "Too many instructions ({}), the 2090 has {} program steps".format(
            len(instr), MIC_MAX_STEPS), 400

    send_busch_instructions(instr)    # synchron, zeitkritisch (ca. 130 ms pro Befehl)

    return "MIC transfer done ({} instructions)".format(len(instr))

# ================= BUZZER =================

buzzer_pwm = PWM(Pin(BUZZER_PIN))
buzzer_pwm.duty_u16(0)

beep_queue = []

def beep(freq, duration_ms=None):
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

# ================= ROUTES =================

@app.get('/')
async def index(req):
    # In 1-KB-Stuecken aus der Datei senden, statt die ganze Seite (ca. 13 KB)
    # als Text und noch einmal als Bytes in den Speicher zu legen.
    return Response.send_file("index.html", content_type="text/html; charset=UTF-8")

def is_userscript(name):
    """Nur userscripts/<name>.py, keine Unterordner, kein .. (Schutz vor Versehen)."""
    if not name.startswith("userscripts/"):
        return False
    f = name[len("userscripts/"):]
    return f.endswith(".py") and len(f) > 3 and "/" not in f and "\\" not in f and not f.startswith(".")

@app.post('/save')
async def save(req):

    name=req.args.get("name","script.py")

    if not is_userscript(name):
        return "Not saved: only .py files in userscripts/ allowed",400

    body=req.body.decode() if isinstance(req.body,bytes) else req.body

    try:
        with open(name,"w") as f:
            f.write(body)
    except Exception as e:
        return "Save failed: "+str(e),500

    problem = script_problem(body)
    if problem:
        return "Saved "+name+" - warning: "+problem+" (Run will refuse it)"
    return "Saved "+name

@app.get('/load')
async def load(req):

    name=req.args.get("name","script.py")

    try:
        with open(name) as f:
            return f.read(),200,{'Content-Type':'text/plain'}
    except OSError:
        return "File not found: "+name,404

@app.get('/run')
async def run(req):

    global current_task

    if current_task and not current_task.done():
        return "Script already running"

    name=req.args.get("name","script.py")

    try:
        with open(name) as f:
            code=f.read()
    except OSError:
        return "File not found: "+name,404

    problem = script_problem(code)
    if problem:
        return "Not started: "+problem,400

    asyncio.create_task(run_user_script(code))

    return "Started "+name

@app.get('/stop')
async def stop(req):

    global current_task

    if current_task:
        current_task.cancel()
        current_task=None
        setOutputs(0)
        stop_sound()
        return "Stopped"

    return "No script"


# ================= LIST PY FILES =================
@app.get("/list_py")
async def list_py(req):
    files = []
    try:
        for f in os.listdir("userscripts"):
            if f.endswith(".py"):
                files.append(f)
    except Exception as e:
        log("Error listing userscripts: "+str(e))
    return files

# ================= WEB TASTER =================
async def reset_taste_after(taste_var, delay_ms=500):
    await asyncio.sleep_ms(delay_ms)
    taste_var["pressed"] = False

@app.get('/set_taste')
async def set_taste(req):
    global current_task
    if not current_task or current_task.done():
        return "No active user script"

    ttype = req.args.get("type","G")
    try:
        val = int(req.args.get("value","0"))
    except ValueError:
        val = 0

    taste_var = tasteH if ttype=="H" else tasteG

    if val==1:
        taste_var["pressed"] = True
        log(f"Key {ttype} pressed")
        asyncio.create_task(reset_taste_after(taste_var,500))

    return "OK"

async def reset_later(delay_ms=500):
    await asyncio.sleep_ms(delay_ms)
    machine.reset()

# POST: Browser wiederholen POST-Anfragen nicht von selbst. Erst antworten, dann
# neu starten - sonst sieht der Browser einen Verbindungsabbruch, schickt die
# Anfrage nach dem Neustart erneut, und der ESP startet immer wieder neu.
@app.post("/reset")
async def reset(req):
    log("ESP restart triggered")
    asyncio.create_task(reset_later())
    return "Restarting..."


@app.get("/matrix_control")
async def matrix_control(req):
    action = req.args.get("action","")

    if action == "start":
        start_matrix_tasks()
        return "Matrix started"

    if action == "stop":
        stop_matrix_tasks()
        return "Matrix stopped"

    return "Invalid action"

# ================= STATUS (eine Abfrage fuer die Weboberflaeche) =================
# Der Browser schickt die zuletzt erhaltenen Versionen (lv = Log, mv = Matrix);
# Log und Matrix kommen nur mit, wenn sie sich geaendert haben. Die Anfrage
# laeuft nur, wenn der Matrix-Task abgibt (zwischen zwei Bildern), und stoert
# das Lesen der Nibbles deshalb nicht.
@app.get("/status")
async def status(req):
    try:
        lv = int(req.args.get("lv", "-1"))
        mv = int(req.args.get("mv", "-1"))
    except ValueError:
        lv = mv = -1
    s = {
        "running": 1 if current_task and not current_task.done() else 0,
        "matrix": 1 if matrix_tasks_running else 0,
        "lv": log_version,
        "mv": np.version,
    }
    if lv != log_version:
        s["log"] = "\n".join(log_buffer)
    if mv != np.version:
        s["px"] = np.hex_rows()   # LED-Bild immer (auch Scripts ohne Matrix-Task)
    return s

# ================= WLAN =================
# Bricht das WLAN im Betrieb ab, wird alle WIFI_CHECK_S Sekunden neu verbunden
# (Zugangsdaten aus wifi.json). Meldungen auf der Konsole und im Web-Log.
WIFI_CHECK_S = 5

def wifi_message(text):
    print(text)
    log(text)

async def wifi_task():
    sta = network.WLAN(network.STA_IF)
    lost = False
    while True:
        await asyncio.sleep(WIFI_CHECK_S)
        if sta.isconnected():
            if lost:
                lost = False
                wifi_message("WiFi reconnected: " + sta.ifconfig()[0])
            continue
        if not lost:
            lost = True
            wifi_message("WiFi lost, reconnecting...")
        try:
            with open("wifi.json") as f:
                cfg = json.load(f)
            sta.disconnect()
            sta.connect(cfg["ssid"], cfg["password"])
        except Exception as e:
            print("WiFi reconnect error:", e)

# ================= MAIN =================
async def main_task():

    asyncio.create_task(buzzer_play_task())
    asyncio.create_task(wifi_task())
    #asyncio.create_task(matrix_display_task())
    #asyncio.create_task(matrix_task())

    log("Server started")

    await app.start_server(port=8080)

asyncio.run(main_task())