import socket
import json
import network
import time
import machine

CONFIG_FILE = "wifi.json"
PORTAL_TIMEOUT_S = 300   # Neustart nach 5 Minuten ohne Eingabe (nur wenn wifi.json existiert)
MAX_REQUEST = 4096

HEADER = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"


def save_config(ssid, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"ssid": ssid, "password": password}, f)


def scan_networks():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    nets = sta.scan()
    ssids = []

    for net in nets:
        try:
            ssid = net[0].decode()
        except Exception:
            continue
        if ssid and ssid not in ssids:   # versteckte Netze (leer) weglassen
            ssids.append(ssid)

    return ssids


def html_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


def web_page(ssids):
    options = ""
    for s in ssids:
        e = html_escape(s)
        options += '<option value="{}">{}</option>'.format(e, e)

    return """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body>
    <h2>WiFi Setup</h2>
    <form method="post">
        SSID:
        <select name="ssid">
            {}
        </select><br><br>

        or enter manually:
        <input name="ssid_manual"><br><br>

        Password:
        <input name="password" type="password"><br><br>

        <input type="submit" value="Save">
    </form>
</body>
</html>
""".format(options)


def urldecode(s):
    # Formular-Kodierung: "+" = Leerzeichen, "%XX" = Byte (UTF-8)
    b = s.replace("+", " ").encode()
    out = bytearray()
    i = 0
    n = len(b)
    while i < n:
        c = b[i]
        if c == 0x25 and i + 2 < n:   # "%" mit zwei folgenden Zeichen
            try:
                out.append(int(b[i + 1:i + 3].decode(), 16))
                i += 3
                continue
            except ValueError:
                pass
        out.append(c)
        i += 1
    return bytes(out).decode()


def parse_body(body):
    params = {}
    for pair in body.split("&"):
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
        else:
            k, v = pair, ""
        params[urldecode(k)] = urldecode(v)
    return params


def parse_post(data):
    try:
        pos = data.find("\r\n\r\n")
        if pos < 0:
            return {}
        return parse_body(data[pos + 4:])
    except Exception:
        return {}


def choose_ssid(params):
    # Eingetipptes Netz hat Vorrang, sonst die Auswahl aus der Liste
    manual = params.get("ssid_manual", "").strip()
    if manual:
        return manual
    return params.get("ssid", "").strip()


def read_request(cl):
    # Liest Kopf und (laut Content-Length) den ganzen Body, auch ueber mehrere Pakete
    data = b""
    while data.find(b"\r\n\r\n") < 0 and len(data) < MAX_REQUEST:
        chunk = cl.recv(512)
        if not chunk:
            break
        data += chunk

    pos = data.find(b"\r\n\r\n")
    if pos < 0:
        return data.decode()

    head = data[:pos].decode()
    length = 0
    for line in head.split("\r\n"):
        if line.lower().startswith("content-length:"):
            try:
                length = int(line.split(":", 1)[1].strip())
            except ValueError:
                length = 0

    while len(data) - (pos + 4) < length and len(data) < MAX_REQUEST:
        chunk = cl.recv(512)
        if not chunk:
            break
        data += chunk

    return data.decode()


def send_all(cl, text):
    data = text.encode()
    if hasattr(cl, "sendall"):
        cl.sendall(data)
    else:
        cl.send(data)


def start(timeout_s=None):
    ssids = scan_networks()
    print("Gefundene Netzwerke:", ssids)

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    s.bind(addr)
    s.listen(1)
    s.settimeout(1)

    print("Config-Webserver: http://192.168.4.1")
    if timeout_s:
        print("Neustart in {} s, falls keine Eingabe erfolgt".format(timeout_s))

    start_time = time.time()

    while True:
        if timeout_s and time.time() - start_time >= timeout_s:
            print("Portal-Timeout - Neustart, neuer WLAN-Versuch")
            s.close()
            machine.reset()
            return

        try:
            cl, addr = s.accept()
        except OSError:
            continue   # kein Client innerhalb 1 s, Timeout pruefen

        try:
            cl.settimeout(5)
            request = read_request(cl)

            if request.startswith("POST"):
                params = parse_post(request)

                ssid = choose_ssid(params)
                password = params.get("password", "")

                if ssid:
                    save_config(ssid, password)

                    send_all(cl, HEADER + "Saved! Restarting...")
                    cl.close()

                    time.sleep(1)   # Antwort noch ausliefern
                    s.close()
                    machine.reset()
                    return

            send_all(cl, HEADER + web_page(ssids))
        except OSError as e:
            print("Portal: Verbindungsfehler", e)
        finally:
            try:
                cl.close()
            except Exception:
                pass
