Die _"Firmware"_ für das ESP2090-Studio (Stand: **v1.5**, 09.11.2026) besteht aus:
- [MicroPython](https://micropython.org/download/ESP32_GENERIC_C3), installiert auf dem ESP32-C3 (erprobt mit 1.27.0 und 1.29.0)
- einigen Python-Skripten, im einzelnen
  - [main.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/main.py) für die eigentliche Funktionalität des ESP2090-Studios
  - [boot.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/boot.py) für GPIO-Initialisierung und Verbindung mit WLAN
  - [hw.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/hw.py) mit der Pinbelegung
  - [matrix_draw.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/matrix_draw.py) mit den Zeichenbefehlen für die LED-Matrix
  - [basicweb.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/basicweb.py) für einen eigenen AP, falls keine WLAN-Verbindung möglich ist
  - [microdot.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/microdot.py) (Version 2.5.1) als Bibliothek für einen schlanken und effizienten Webserver
  - [webrepl_cfg.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/webrepl_cfg.py) mit dem WebREPL-Passwort (bitte vor dem Hochladen ändern)
- der HTML-Webseite [index.html](https://github.com/rab-berlin/ESP2090/blob/main/firmware/index.html)

**Installation:** siehe [ANLEITUNG.txt](https://github.com/rab-berlin/ESP2090/blob/main/firmware/ANLEITUNG.txt) – empfohlen und erprobt mit [Thonny](https://thonny.org), das danach wieder deinstalliert werden kann, wenn es nicht gebraucht wird. Die Skripte `install_windows.bat` und `install_mac_linux.sh` (mpremote) sind nicht getestet.

Die WLAN-Zugangsdaten stehen in **wifi.json** (Vorlage: `wifi.json.beispiel`). Fehlt sie, startet der ESP im Einrichtungsmodus (WLAN „ESP32-Setup“) und fragt im Browser nach dem Netz.

**Wichtig:** Auf dem ESP32 muss der Ordner **userscripts** existieren – er enthält die Python-Skripte, die zur Laufzeit geladen und gestartet werden. Ohne ihn funktionieren Speichern, Laden und die Dateiliste in der Weboberfläche nicht. Beim Hochladen mit Thonny also den Ordner `userscripts` mit auswählen.

Die Weboberfläche läuft auf Port 8080: `http://<IP-Adresse>:8080`. Links der Editor für User-Skripte, in der Mitte das Log und die Web-Taster G/H, rechts die LED-Matrix (live) mit den Knöpfen für Matrix an/aus, MIC-Upload zum 2090 und ESP-Reset.

In User-Skripten kann auf folgende Objekte und Funktionen des ESP2090-Studios zugegriffen werden:

- Ausgänge des ESP (**out_1** bis **out_4**) - damit werden die Eingänge des Microtronic angesteuert
- Eingänge des ESP (**in_1** bis **in_4**) - damit werden die Ausgänge des Microtronic gelesen
- Objekte **tasteG** und **tasteH** - die entsprechenden Buttons auf der Weboberfläche (`tasteG["pressed"]`)
- Funktion **setOutputs(wert)** - setzt out_1 bis out_4 auf den binären Wert des Aufruf-Parameters
- Funktion **getInputs()** - liest in_1 bis in_4 als Zahl 0-15
- Funktion **log(text)** - schreibt ins Log
- Funktion **beep(frequenz, dauer_ms)** - erzeugt einen Ton; ohne Dauer klingt er, bis der nächste Ton kommt (`beep(0)` = aus)
- Funktion **setColors(liste)** - legt die Anzeigefarben der LEDs fest: eine Liste mit **64 Farbnamen**, oberste Zeile zuerst (`"schwarz"`, `"rot"`, `"orange"`, `"gelb"`, `"gruen"`, `"tuerkis"`, `"blau"`, `"violett"`, `"magenta"`, `"weiss"`). Wer seine Farben als 8x8-Matrix schreibt, übergibt `[c for zeile in matrix for c in zeile]`.
- Funktion **setPalette(nummer, (r, g, b))** - ändert eine der 16 Farben der Palette, z. B. `setPalette(10, (5, 0, 5))`
- Das gesamte Neopixel-Objekt **np** für komplexere Anforderungen an die LED-Matrix. Die Helligkeit ist zum Schutz der USB-Versorgung begrenzt (`LED_MAX_MA = 250` in main.py; mit eigenem Netzteil ab 2 A bis etwa 1000).

Das alles kann natürlich selbst in der main.py geändert werden. Ich selbst ändere es praktisch andauernd... also keine Garantie, dass dieser Text den jeweils aktuellsten Stand wiedergibt.

User-Skripte laufen als Task neben Webserver und Matrix (kooperatives Multitasking mit asyncio). Der Code wird automatisch in eine `async`-Funktion verpackt, `await` kann also direkt verwendet werden. Damit die anderen Tasks, insbesondere der Webserver, nicht "sterben", sollten User-Skripte
- kurz sein und praktisch gleich wieder enden oder
- in jeder Schleife mit `await asyncio.sleep_ms(...)` warten statt mit `sleep`, um die Kontrolle an andere Tasks zu übergeben.

Vor dem Start prüft der ESP das Skript und startet es **nicht**, wenn eine `while`- oder `for`-Schleife kein `await` enthält (Ausnahme: `for ... in range(n)` mit fester Zahl bis 64) oder wenn `time.sleep`, `sleep_ms`, `sleep_us` oder `input()` vorkommen. Beim Speichern erscheint schon eine Warnung. Nach dem Ende oder bei „Stop“ werden die Ausgänge auf 0 gesetzt und ein Ton beendet.

Gespeichert werden kann nur im Ordner `userscripts/` (Dateien `*.py`).

Ein Beispiel liegt in [userscripts/beispiel_lauflicht.py](https://github.com/rab-berlin/ESP2090/blob/main/firmware/userscripts/beispiel_lauflicht.py).
