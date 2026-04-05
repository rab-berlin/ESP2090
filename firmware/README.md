Die _"Firmware"_ für das ESP2090-Studio besteht aus:
- MicroPython, installiert auf dem ESP32-C3
- einigen Python-Skripten, im einzelnen
  - main.py für die eigentliche Funktionalität des ESP2090-Studios
  - boot.py für GPIO-Initialisierung und Verbindung mit WLAN
  - basicweb.py für einen eigenen AP, falls keine WLAN-Verbindung möglich ist
  - microdot.py als Bibliothek für den schlanken und effizienten Microdot-Webserver
- einer HTML-Webseite index.html

Später werden noch folgende Dateien erzeugt:
- wifi.json für die WLAN-Credentials
- webrepl_cfg.py für die REPL-Credentials, falls z.B. Thonny verwendet wird

Außerdem gibt es noch zwei Ordner auf dem ESP32:
- logs für die Logdateien
- userscripts für die Python-Skripte, die zur Laufzeit geladen und gestartet werden

In User-Skripten kann auf folgende Objekte und Funktionen des ESP2090-Studios zugegriffen werden:

- Ausgänge des ESP (**out_1** bis **out_4**) - damit werden die Eingänge des Microtronic angesteuert
- Eingänge des ESP (**in_1** bis **in_4**) - damit werden die Ausgänge des Microtronic gelesen
- Objekte **tasteG** und **tasteH** - die entsprechenden Buttons auf der Weboberfläche
- Funktion **setOutputs** - setzt out_1 bis out_4 auf den binären Wert des Aufruf-Parameters
- Funktion **log** - schreibt ins Log
- Funktion **beep** - erzeugt Ton mit übergebener Frequenz
- Funktion **setColors** - legt mit einer Matrix die Anzeigefarben der LEDs fest
- Das gesamte Neopixel-Objekt **np** für komplexere Anforderungen an die LED-Matrix

Das alles kann natürlich selbst in der main.py geändert werden. Ich selbst ändere es praktisch andauernd... also keine Garantie, dass dieser Text den jeweils aktuellsten Stand wiedergibt.

Damit die anderen Tasks, insbesondere der Webserver, nicht "sterben", sollten User-Skripte 
- kurz sein und praktisch gleich wieder enden oder
- den asyncio-Regeln für kooperatives Multitasking folgen:
  - Aufruf-Syntax mit _async def ..._ statt _def ..._
  - innerhalb der Funktion warten mit _await_ statt _sleep_, um die Kontrolle an andere Tasks zu übergeben
 
 
