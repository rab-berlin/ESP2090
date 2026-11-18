# Firmware-Version: bei jeder Aenderung an den Geraetedateien erhoehen
# (auch in README.md, Abschnitt Versionen). Angezeigt in der Weboberflaeche.
FW_VERSION = "1.8"

# Die Firmware ist auf mehrere Dateien verteilt, damit der ESP beim Start nie eine
# grosse Datei auf einmal uebersetzen muss (Speicher). Reihenfolge: die groesste
# Datei (microdot) zuerst, solange der Speicher noch frei ist; dazwischen aufraeumen.
#   core.py     Log, Ein-/Ausgaenge zum 2090, Web-Taster, Buzzer
#   matrix.py   LED-Matrix (zeitkritischer Lese-Task)
#   scripts.py  Userscripts: Pruefung, Ausfuehren, Stop
#   upload.py   Upload zum 2090 (.mic)
#   main.py     Webserver (alle Adressen), WLAN, Autostart, Start
import gc
from microdot import Microdot, Response
gc.collect()
import uasyncio as asyncio
import machine, network, os, json
import core
gc.collect()
import matrix
gc.collect()
import scripts
gc.collect()
import upload
gc.collect()
from core import log

app = Microdot()

# ================= UPLOAD =================
@app.post('/busch_upload')
async def busch_upload(req):
    instr, err = upload.parse_request(req.body or b"", req.headers.get("Content-Type", ""))
    if err:
        return err

    # Der Upload benutzt dieselben Leitungen: laufendes Userscript und Matrix vorher stoppen
    if scripts.stop_user_script():
        log("User script stopped for upload")
    if matrix.matrix_tasks_running:
        matrix.stop_matrix_tasks()
        log("LED matrix stopped for upload")

    upload.send_busch_instructions(instr)    # synchron, zeitkritisch (ca. 130 ms pro Befehl)

    return "MIC transfer done ({} instructions)".format(len(instr))

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

    problem = scripts.script_problem(body)
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

    if scripts.is_running():
        return "Script already running"

    name=req.args.get("name","script.py")

    try:
        with open(name) as f:
            code=f.read()
    except OSError:
        return "File not found: "+name,404

    problem = scripts.script_problem(code)
    if problem:
        return "Not started: "+problem,400

    asyncio.create_task(scripts.run_user_script(code))

    return "Started "+name

@app.get('/stop')
async def stop(req):
    return "Stopped" if scripts.stop_user_script() else "No script"


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
    if not scripts.is_running():
        return "No active user script"

    ttype = req.args.get("type","G")
    try:
        val = int(req.args.get("value","0"))
    except ValueError:
        val = 0

    taste_var = core.tasteH if ttype=="H" else core.tasteG

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
        matrix.start_matrix_tasks()
        return "Matrix started"

    if action == "stop":
        matrix.stop_matrix_tasks()
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
    con = req.args.get("con")
    if con in ("0", "1"):
        matrix.CONSOLE_MATRIX = con == "1"
    np = matrix.np
    s = {
        "running": 1 if scripts.is_running() else 0,
        "matrix": 1 if matrix.matrix_tasks_running else 0,
        "sleep": 1 if matrix.matrix_tasks_running and matrix.matrix_asleep else 0,
        "mem": gc.mem_free() if hasattr(gc, "mem_free") else 0,
        "lv": core.log_version,
        "mv": np.version,
    }
    if lv != core.log_version:
        s["log"] = "\n".join(core.log_buffer)
    if mv != np.version and req.args.get("px") != "0":
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

# ================= AUTOSTART =================
# autostart.json: {"script": "userscripts/x.py", "led": true}. Fehlt die Datei,
# startet nichts automatisch. Nach AUTOSTART_DELAY_MS: erst LED, dann Script
# (mit derselben Pruefung wie Run).
AUTOSTART_FILE = "autostart.json"
AUTOSTART_DELAY_MS = 2000

def autostart_config():
    try:
        with open(AUTOSTART_FILE) as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    script = cfg.get("script") or ""
    return {"script": script if is_userscript(script) else "", "led": bool(cfg.get("led"))}

def autostart_save(cfg):
    if not cfg["script"] and not cfg["led"]:
        try:
            os.remove(AUTOSTART_FILE)
        except OSError:
            pass
        return
    with open(AUTOSTART_FILE, "w") as f:
        json.dump(cfg, f)

@app.get("/version")
async def version(req):
    return FW_VERSION

@app.get("/autostart")
async def autostart_get(req):
    return autostart_config()

# Aendern per POST: ?script=userscripts/x.py (leer = kein Script) und/oder ?led=0|1
@app.post("/autostart")
async def autostart_set(req):
    cfg = autostart_config()
    script = req.args.get("script")
    if script is not None:
        if script and not is_userscript(script):
            return "Autostart: only .py files in userscripts/ allowed", 400
        cfg["script"] = script
    led = req.args.get("led")
    if led in ("0", "1"):
        cfg["led"] = led == "1"
    try:
        autostart_save(cfg)
    except OSError as e:
        return "Autostart not saved: " + str(e), 500
    return cfg

async def autostart_task():
    cfg = autostart_config()
    if not cfg["script"] and not cfg["led"]:
        return
    await asyncio.sleep_ms(AUTOSTART_DELAY_MS)
    if cfg["led"] and not matrix.matrix_tasks_running:
        log("Autostart: LED matrix")
        matrix.start_matrix_tasks()
    name = cfg["script"]
    if not name:
        return
    if scripts.is_running():
        return                              # inzwischen von Hand gestartet
    try:
        with open(name) as f:
            code = f.read()
    except OSError:
        log("Autostart: file not found: " + name)
        return
    problem = scripts.script_problem(code)
    if problem:
        log("Autostart: not started: " + problem)
        return
    log("Autostart: " + name)
    asyncio.create_task(scripts.run_user_script(code))

# ================= MAIN =================
async def main_task():

    asyncio.create_task(core.buzzer_play_task())
    asyncio.create_task(wifi_task())
    asyncio.create_task(autostart_task())

    print("ESP2090 firmware v" + FW_VERSION)
    log("Server started, firmware v" + FW_VERSION)

    await app.start_server(port=8080)

asyncio.run(main_task())
