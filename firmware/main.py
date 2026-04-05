import uasyncio as asyncio
from microdot import Microdot
from machine import Pin, PWM
import machine, network, gc, time, os
import neopixel
import sys

# ================= GPIO =================
# out_1 - out_4, in_1 - in_4 in boot.py 

OUTPUTS = [out_1, out_2, out_3, out_4]
INPUTS = [in_1, in_2, in_3, in_4]

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
    
def getInputsList():
    return [pin.value() for pin in INPUTS]

def getInputsNumber():
    # noch dummy
    return 0

# ================= LED MATRIX =================

matrix_tasks_running = False
matrix_display_task_handle = None
matrix_task_handle = None

LED_PIN = 2
ROWS = 8
COLS = 8
NUM_LEDS = ROWS * COLS

WAIT_AFTER_REQ = 30000
WAIT_AFTER_ACK = 13500
NIBBLE_INTERVAL = 9217
NUM_NIBBLES = 16
POST_DISPLAY_WAIT = 30000

COLORS = {
    "rot":     (10,0,0),
    "orange":  (10,4,0),
    "gelb":    (10,10,0),
    "gruen":   (0,8,0),
    "tuerkis": (0,8,6),
    "blau":    (0,0,10),
    "violett": (6,0,10),
    "magenta": (10,0,6),
    "weiss":   (10,10,10),
    "schwarz": (0,0,0),
}
COLOR_OFF = (0,0,0)

np = neopixel.NeoPixel(Pin(LED_PIN), NUM_LEDS)

matrix_dirty = True # initial
matrix = bytearray(NUM_LEDS)
color_matrix = [[None]*COLS for _ in range(ROWS)]


def phys_index(row, col):
    """
    Liefert den physischen NeoPixel-Index für ein Pixel an
    logischer Position (row, col) in einer 8x8-Matrix.
    
    Annahme physische Verdrahtung:
    Pixel 0 = unten links
    Pixel 1 = direkt darueber
    Pixel 8 = rechts neben Pixel 0
    """
    return col * ROWS + row


def start_matrix_tasks():
    global matrix_display_task_handle, matrix_task_handle, matrix_tasks_running

    if matrix_tasks_running:
        log("LED task already running")
        return

    matrix_display_task_handle = asyncio.create_task(matrix_display_task())
    matrix_task_handle = asyncio.create_task(matrix_task())

    matrix_tasks_running = True
    log("LED task started")


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

    matrix_tasks_running = False
    log("LED task stopped")


def clearPixel(pos):
    matrix[pos] = 0
    matrix_dirty = True

def setPixel(pos):
    matrix[pos] = 1
    print(matrix)
    matrix_dirty = True


def setColors(new_matrix):
    """
    Setzt die komplette 8x8 color_matrix auf new_matrix.
    new_matrix muss 8x8 sein.
    """
    global color_matrix
    if len(new_matrix) != ROWS or any(len(row) != COLS for row in new_matrix):
        log("Fehler: Color-Matrix muss 8x8 sein")
        return
    color_matrix = new_matrix[::-1]


async def matrix_display_task():
    global matrix_dirty

    while True:

        if matrix_dirty:

            for r in range(ROWS):
                for c in range(COLS):

                    index = phys_index(r, c)

                    if matrix[r*COLS + c]:  # Zugriff auf 1D-Array
                        cname = color_matrix[r][c]
                        color = COLORS.get(cname, COLORS["rot"])
                        np[index] = color
                    else:
                        np[index] = COLOR_OFF

            np.write()
            matrix_dirty = False
            matrix_print_console(matrix)

        await asyncio.sleep_ms(50)


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

    while True:
                
        # =========================
        # 1. REQ setzen
        # =========================
        out_1.value(1)  # REQ = HIGH
        req_time = time.ticks_us()
        ack_time = None

        # =========================
        # 2. Auf ACK warten (max 18 ms)
        # =========================
        while True:
                        
            now = time.ticks_us()
            elapsed = time.ticks_diff(now, req_time)

            # ACK = 0001
            if in_1.value():
                ack_time = time.ticks_us()
                out_1.value(0)  # REQ sofort LOW
                #print(time.ticks_diff(ack_time, req_time))
                break

            # Timeout
            if elapsed >= WAIT_AFTER_REQ:
                out_1.value(0)
                # kein ACK einfach neuer Versuch
                break

        if ack_time is None:
            # Retry (kleine Pause damit CPU nicht stirbt)
            #await asyncio.sleep_ms(0)
            continue # zum Schleifenanfang

        # =========================
        # 3. MSB_WAIT_TIME warten blocking
        # =========================
        start_time = time.ticks_add(ack_time, WAIT_AFTER_ACK)
        while time.ticks_diff(start_time, time.ticks_us()) > 0:
            pass

        # =========================
        # 4. Daten einlesen
        # =========================
        next_time = time.ticks_add(start_time, NIBBLE_INTERVAL)
        idx = 0
        
        for _ in range(NUM_NIBBLES):
            while time.ticks_diff(next_time, time.ticks_us()) > 0:
                pass
            matrix[idx] = in_1.value(); idx += 1
            matrix[idx] = in_2.value(); idx += 1
            matrix[idx] = in_3.value(); idx += 1
            matrix[idx] = in_4.value(); idx += 1
            next_time = time.ticks_add(next_time, NIBBLE_INTERVAL)
            
        matrix_dirty = True

        # =========================
        # 5. Mini-Yield für asyncio
        # =========================
        await asyncio.sleep_ms(20)



# ================= SERVER =================
app = Microdot()
current_task = None
LOG_SIZE = 40
log_buffer = []

# ================= FILE LOGGING =================
LOG_DIR = "logs"
file_log_buffer = []

def ensure_log_dir():
    try:
        os.mkdir(LOG_DIR)
    except:
        pass

def current_log_filename():
    t = time.localtime()
    return "{}/log_{:04d}-{:02d}-{:02d}.txt".format(LOG_DIR, t[0], t[1], t[2])

def log(msg):
    msg = str(msg)[:100]
    log_buffer.append(msg)
    file_log_buffer.append(msg)
    if len(log_buffer) > LOG_SIZE:
        log_buffer.pop(0)

def flush_now():
    if file_log_buffer:
        try:
            ensure_log_dir()
            fname = current_log_filename()
            with open(fname, "a") as f:
                for line in file_log_buffer:
                    f.write(line + "\n")
            file_log_buffer.clear()
        except Exception as e:
            log("Log error "+str(e))

async def flush_task():
    while True:
        await asyncio.sleep(5)
        flush_now()

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
            "tasteG":tasteG,
            "tasteH":tasteH,
            "setOutputs":setOutputs,
            "log":log,
            "beep":beep,
            "setColors":setColors,
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

def send_busch_file(filename):

    log("Busch upload started")

    try:
        with open(filename) as f:
            for line in f:

                line=line.strip().upper()

                if len(line)<3:
                    continue

                instr=(line[0:3]
                    .replace("I","1")
                    .replace("L","1")
                    .replace("O","0")
                    .replace("Q","0"))

                if is_valid(instr):
                    load_instruction_to_busch2090(instr)

    except:
        log("Upload file missing")

    setOutputs(0)
    log("Busch upload finished")

@app.post('/busch_upload')
async def busch_upload(req):

    filename="busch_upload.mic"

    body=req.body
    sep=b"\r\n\r\n"

    start=body.find(sep)+len(sep)
    data=body[start:]

    end=data.rfind(b"\r\n------")

    if end>0:
        data=data[:end]

    with open(filename,"wb") as f:
        f.write(data)

    send_busch_file(filename)

    return "Busch transfer done"

# ================= BUZZER =================

BUZZER_PIN = 10
buzzer_pwm = PWM(Pin(BUZZER_PIN))
buzzer_pwm.duty_u16(0)

beep_queue = []

def beep(freq,duration_ms):
    beep_queue.append((freq,duration_ms))

async def buzzer_play_task():
    while True:
        if beep_queue:
            freq,dur=beep_queue.pop(0)
            if freq>0:
                buzzer_pwm.freq(freq)
                buzzer_pwm.duty_u16(20000)
            else:
                buzzer_pwm.duty_u16(0)
            await asyncio.sleep_ms(dur)
            buzzer_pwm.duty_u16(0)
        else:
            await asyncio.sleep_ms(10)

# ================= ROUTES =================

@app.get('/')
async def index(req):
    with open("index.html") as f:
        return f.read(),200,{'Content-Type':'text/html'}

@app.get('/logs')
async def logs(req):
    return "\n".join(log_buffer),200,{'Content-Type':'text/plain'}

@app.post('/save')
async def save(req):

    name=req.args.get("name","script.py")

    body=req.body.decode() if isinstance(req.body,bytes) else req.body

    with open(name,"w") as f:
        f.write(body)

    return "Saved "+name

@app.get('/load')
async def load(req):

    name=req.args.get("name","script.py")

    try:
        with open(name) as f:
            return f.read(),200,{'Content-Type':'text/plain'}
    except:
        return "File not found"

@app.get('/run')
async def run(req):

    global current_task

    if current_task and not current_task.done():
        return "Script already running"

    name=req.args.get("name","script.py")

    try:
        with open(name) as f:
            code=f.read()
    except:
        return "File not found"

    asyncio.create_task(run_user_script(code))

    return "Started "+name

@app.get('/stop')
async def stop(req):

    global current_task

    if current_task:
        current_task.cancel()
        current_task=None
        setOutputs(0)
        flush_now()
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
    except:
        val = 0

    taste_var = tasteH if ttype=="H" else tasteG

    if val==1:
        taste_var["pressed"] = True
        log(f"Taste {ttype} pressed")
        asyncio.create_task(reset_taste_after(taste_var,500))

    return "OK"

@app.get("/reset")
async def reset(req):
    log("ESP restart triggered")
    await asyncio.sleep_ms(100)
    machine.reset()
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

# ================= CHECK SCRIPT RUNNING =================
@app.get("/is_script_running")
async def is_script_running(req):
    return "1" if current_task and not current_task.done() else "0"


# ================= MAIN =================
async def main_task():

    asyncio.create_task(flush_task())
    asyncio.create_task(buzzer_play_task())
    #asyncio.create_task(matrix_display_task())
    #asyncio.create_task(matrix_task())

    log("Server started")

    await app.start_server(port=8080)

asyncio.run(main_task())