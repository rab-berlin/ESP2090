from machine import Pin
import network
import time
import json
import webrepl

CONFIG_FILE = "wifi.json"

# ================= GPIO =================
out_1 = Pin(20, Pin.OUT)
out_2 = Pin(21, Pin.OUT)
out_3 = Pin(4, Pin.OUT)
out_4 = Pin(3, Pin.OUT)

in_1 = Pin(5, Pin.IN, Pin.PULL_DOWN)
in_2 = Pin(6, Pin.IN, Pin.PULL_DOWN)
in_3 = Pin(7, Pin.IN, Pin.PULL_DOWN)
in_4 = Pin(8, Pin.IN, Pin.PULL_DOWN)


def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
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
if connect_wifi():
    webrepl.start()
    print("WebREPL WLAN active")

else:
    start_ap()

    webrepl.start()
    print("WebREPL AP active")

    # HIER bewusst blocking!
    import basicweb
    basicweb.start()