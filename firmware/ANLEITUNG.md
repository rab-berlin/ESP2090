# ESP2090-Studio – Installation auf einem neuen ESP32-C3 SuperMini

## Inhalt

Alles liegt im Ordner `firmware` (im GitHub-Repo rab-berlin/ESP2090).

**Auf den ESP kommen:**

- `boot.py`, `hw.py`, `main.py`, `core.py`, `matrix.py`, `scripts.py`, `upload.py`, `matrix_draw.py`, `basicweb.py`, `microdot.py`, `index.html`, `webrepl_cfg.py`
- `userscripts/beispiel_lauflicht.py` (Beispiel, kann gelöscht werden)

**Nur auf dem PC bleiben:**

| Datei | Inhalt |
|---|---|
| `README.md` | Beschreibung der Firmware und der Funktionen für Userscripts |
| `wifi.json.beispiel` | Vorlage für die WLAN-Zugangsdaten |
| `install_windows.bat` | optional: Kopieren per Doppelklick (mpremote, nicht getestet) |
| `install_mac_linux.sh` | optional: dasselbe für Mac/Linux |
| `ANLEITUNG.md` | diese Datei |

## Was du brauchst

- ESP32-C3 SuperMini und ein USB-C-**Daten**kabel (kein reines Ladekabel!)
- [Thonny](https://thonny.org) (kostenlos). Damit wird installiert (empfohlen und erprobt). Danach kann Thonny wieder deinstalliert werden, wenn es nicht gebraucht wird.

## Schritt 1: MicroPython auf den ESP flashen (einmalig)

MicroPython-Version: Auf dem ESP erprobt mit 1.27.0 und 1.29.0. Thonny installiert meist die neueste Version; tritt mit einer neueren Version ein Problem auf, die Version 1.29.0 wählen.

1. Thonny installieren und starten.
2. Den ESP per USB anschließen. Wird er nicht erkannt: BOOT-Taste gedrückt halten, USB einstecken, BOOT loslassen. Dann ist er im Download-Modus.
3. In Thonny: Menü *Werkzeuge → Optionen… → Reiter Interpreter* (englisch: *Tools → Options → Interpreter*).
4. Interpreter **MicroPython (ESP32)** wählen.
5. Unten rechts auf *MicroPython installieren oder aktualisieren (esptool)* klicken (englisch: *Install or update MicroPython (esptool)*).
6. Im Dialog einstellen:

   | | |
   |---|---|
   | Port | der USB-Port des ESP (z. B. `COM5` bzw. `/dev/ttyACM0`) |
   | Familie | ESP32-C3 |
   | Variante | Espressif – ESP32-C3 |
   | Version | die neueste angebotene |

   Dann *Installieren* klicken und warten, bis „Done“ erscheint.
7. Dialog schließen, ESP kurz abstecken und wieder anstecken. Im Thonny-Fenster *Kommandozeile* (Shell) erscheint jetzt `>>>`.

## Schritt 2: WLAN-Zugang festlegen (empfohlen)

1. Die Datei `wifi.json.beispiel` kopieren und die Kopie in `wifi.json` umbenennen.
2. Mit einem Texteditor öffnen und WLAN-Name und Passwort eintragen:

   ```json
   {"ssid": "MeinWLAN", "password": "MeinPasswort"}
   ```

   Die Anführungszeichen müssen stehen bleiben.

Ohne `wifi.json` startet der ESP im Einrichtungsmodus, siehe [Ohne wifi.json](#ohne-wifijson-einrichtungsmodus). Der Weg über `wifi.json` ist zuverlässiger.

## Schritt 3: Dateien auf den ESP kopieren

### Variante A – mit Thonny (empfohlen, erprobt)

1. In Thonny: Menü *Ansicht → Dateien* einschalten.
2. Oben im Dateien-Bereich (*Dieser Computer*) in den Ordner `firmware` wechseln.
3. Diese Dateien **und den Ordner `userscripts`** markieren: `boot.py`, `hw.py`, `main.py`, `core.py`, `matrix.py`, `scripts.py`, `upload.py`, `matrix_draw.py`, `basicweb.py`, `microdot.py`, `index.html`, `webrepl_cfg.py` (nicht: `ANLEITUNG.md`, `README.md`, install-Skripte, `wifi.json.beispiel`). Rechtsklick → *Hochladen nach /* (englisch: *Upload to /*).

   > **Wichtig:** Der Ordner `userscripts` muss mit auf den ESP! Ohne ihn funktionieren Speichern, Laden und die Dateiliste in der Weboberfläche nicht.
4. Die eigene `wifi.json` (aus Schritt 2) ebenso hochladen.
5. Prüfen: Unten im Bereich *MicroPython-Gerät* müssen jetzt stehen: `boot.py`, `hw.py`, `main.py`, `core.py`, `matrix.py`, `scripts.py`, `upload.py`, `matrix_draw.py`, `basicweb.py`, `microdot.py`, `index.html`, `webrepl_cfg.py`, `wifi.json` und der Ordner `userscripts`.

### Variante B – per Skript mit mpremote (nicht getestet)

1. Thonny schließen (es darf nicht mit dem ESP verbunden sein).
2. Einmalig mpremote installieren: `pip install mpremote`
3. Die eigene `wifi.json` neben die install-Skripte legen.
4. `install_windows.bat` doppelklicken bzw. unter Mac/Linux: `sh install_mac_linux.sh`

## Schritt 4: Starten und aufrufen

1. Am ESP die RST-Taste drücken oder USB kurz abziehen.
2. In der Thonny-Shell erscheint nach einigen Sekunden z. B.:

   ```
   Connected: ('192.168.178.42', '255.255.255.0', ...)
   ```

   Die erste Zahl ist die IP-Adresse. Alternativ im Router nachsehen.
3. Im Browser öffnen: `http://<IP-Adresse>:8080`, zum Beispiel `http://192.168.178.42:8080`. Das `:8080` am Ende nicht vergessen.

## Ohne wifi.json: Einrichtungsmodus

1. Der ESP öffnet ein eigenes WLAN **ESP32-Setup**, Passwort: `12345678`.
2. Mit dem Handy oder PC verbinden und `http://192.168.4.1` aufrufen.
3. WLAN aus der Liste wählen **oder** den Namen im Feld *or enter manually* eintippen (z. B. für versteckte Netze). Ein eingetippter Name hat Vorrang vor der Liste. Passwort eingeben (Sonderzeichen und Umlaute sind erlaubt) und absenden.
4. Nach „Saved! Restarting...“ verbindet sich der ESP mit dem WLAN.

Gibt es schon eine `wifi.json`, ist das WLAN beim Start aber nicht erreichbar (z. B. Router nach Stromausfall noch nicht bereit), öffnet der ESP ebenfalls das Einrichtungsportal. Ohne Eingabe startet er nach 5 Minuten neu und versucht es erneut.

## WebREPL (optional)

WebREPL ist aktiv. Das Passwort steht in `webrepl_cfg.py` („ichbins“). Bitte **vor dem Hochladen ändern** (4 bis 9 Zeichen) – das Standard-Passwort ist öffentlich bekannt. Zugang über <https://micropython.org/webrepl> → `ws://<IP-Adresse>:8266`

## Hinweise zum Betrieb

- **Einschaltreihenfolge:** zuerst die Erweiterung (ESP), dann den 2090. Beim Ausschalten umgekehrt.
- **Wichtig:** Der Ordner `userscripts` muss auf dem ESP existieren, sonst funktionieren Speichern, Laden und Dateiliste in der Weboberfläche nicht. Fehlt er, in Thonny im Bereich *MicroPython-Gerät* per Rechtsklick → *Neuer Ordner…* (englisch: *New directory…*) anlegen und `userscripts` nennen.
- **Autostart:** Das Häkchen *Autostart script* unter der Dateizeile startet das Script aus dem Namensfeld nach dem Einschalten, das Häkchen *Autostart* neben *LED on* die LED-Matrix. Gespeichert wird das in `autostart.json` auf dem ESP. Macht ein Autostart-Script Probleme: in Thonny verbinden (das unterbricht `main.py`) und `autostart.json` auf dem ESP löschen.
- **Userscripts** laufen neben Webserver und Matrix. Vor dem Start prüft der ESP sie und startet sie nicht, wenn
  - eine `while`- oder `for`-Schleife kein `await` enthält (Ausnahme: `for ... in range(n)` mit fester Zahl bis 64),
  - `time.sleep` / `sleep_ms` / `sleep_us` oder `input()` vorkommt.

  Pausen in Schleifen: `await asyncio.sleep_ms(20)`. Beim Speichern erscheint bereits eine Warnung (orange), gespeichert wird trotzdem.

## Fehlersuche

| Problem | Abhilfe |
|---|---|
| Thonny findet den ESP nicht | anderes USB-Kabel probieren (viele Kabel können nur laden), BOOT-Taste beim Einstecken halten (siehe Schritt 1) |
| Thonny meldet „Device is busy“ oder reagiert nicht | In Thonny auf *Stop/Neustart* (rotes Stoppschild) klicken. Das unterbricht das laufende Programm auf dem ESP. |
| Webseite nicht erreichbar | Port 8080 in der Adresse? PC im selben WLAN wie der ESP? |
| Falsche WLAN-Daten eingegeben | In Thonny die Datei `wifi.json` auf dem ESP löschen oder korrigieren und den ESP neu starten. |
| Seite lädt nicht, Thonny meldet `MemoryError` beim Start | Prüfen, ob alle Dateien aktuell sind. Hilft das nicht: `microdot.py` auf dem PC vorübersetzen (`pip install mpy-cross`, dann `mpy-cross microdot.py`), `microdot.mpy` hochladen und `microdot.py` auf dem ESP löschen. Siehe README, Abschnitt zur Firmware. |
