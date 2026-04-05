Die "Firmware" für das ESP2090-Studio besteht aus:
- MicroPython für den ESP32-C3
- einigen Python-Skripten, im einzelnen
  - main.py für die eigentliche Funktionalität des ESP2090-Studios
  - boot.py für GPIO-Initialisierung und Verbindung mit WLAN
  - basicweb.py für eigenen AP, falls keine WLAN-Verbindung möglich ist
  - microdot.py als Bibliothek für den schlanken und effizienten Microdot-Webserver
- einer HTML-Webseite index.html
- wifi.json für die WLAN-Credentials
- webrepl_cfg.py für die REPL-Credentials, falls z.B. Thonny verwendet wird
