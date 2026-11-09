import network
import time
import json
import webrepl

CONFIG_FILE = "wifi.json"

# ================= GPIO =================
from hw import OUTPUTS     # Pinbelegung in hw.py

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (OSError, ValueError):   # fehlt oder kein gueltiges JSON
        return None

def connect_wifi():
    cfg = load_config()
    if not cfg:
        return False

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(cfg["ssid"], cfg["password"])

    print("Connecting WiFi...")

    for _ in range(10):
        if sta.isconnected():
            print("Connected:", sta.ifconfig())
            return True
        time.sleep(1)

    return False

def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="ESP32-Setup", password="12345678")
    print("AP aktiv:", ap.ifconfig())


# MAIN

for out in OUTPUTS:
    out.value(0)

if connect_wifi():
    webrepl.start()
    print("WebREPL WLAN active")

else:
    start_ap()

    webrepl.start()
    print("WebREPL AP active")

    # HIER bewusst blocking!
    # Gibt es schon eine wifi.json (WLAN nur gerade nicht erreichbar, z. B. nach
    # Stromausfall), startet das Portal nach PORTAL_TIMEOUT_S neu und versucht es erneut.
    import basicweb
    basicweb.start(timeout_s=basicweb.PORTAL_TIMEOUT_S if load_config() else None)