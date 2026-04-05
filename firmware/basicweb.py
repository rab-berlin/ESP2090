import socket
import json
import network

CONFIG_FILE = "wifi.json"

def save_config(ssid, password):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"ssid": ssid, "password": password}, f)

def scan_networks():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    nets = sta.scan()
    ssids = []

    for net in nets:
        ssid = net[0].decode()
        if ssid not in ssids:
            ssids.append(ssid)

    return ssids

def web_page(ssids):
    options = ""
    for s in ssids:
        options += '<option value="{}">{}</option>'.format(s, s)

    return """\
HTTP/1.1 200 OK

<html>
    <h2>WiFi Setup</h2>
    <form method="post">
        SSID:
        <select name="ssid">
            {}
        </select><br><br>

        oder manuell:
        <input name="ssid"><br><br>

        Passwort:
        <input name="password" type="password"><br><br>

        <input type="submit">
    </form>
</html>
""".format(options)

def parse_post(data):
    try:
        body = data.split("\r\n\r\n")[1]
        params = {}

        for pair in body.split("&"):
            k, v = pair.split("=")
            params[k] = v.replace("%20", " ")

        return params
    except:
        return {}

def start():
    ssids = scan_networks()
    print("Gefundene Netzwerke:", ssids)

    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    print("Config-Webserver: http://192.168.4.1")

    while True:
        cl, addr = s.accept()
        request = cl.recv(1024).decode()

        if "POST" in request:
            params = parse_post(request)

            ssid = params.get("ssid", "")
            password = params.get("password", "")

            if ssid:
                save_config(ssid, password)

                cl.send("HTTP/1.1 200 OK\r\n\r\nGespeichert! Neustart...")
                cl.close()

                import machine
                machine.reset()
                return

        cl.send(web_page(ssids))
        cl.close()