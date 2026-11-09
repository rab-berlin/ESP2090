# Userscripts: der ESP2090 als Peripherie für den Microtronic

Ein Userscript ist ein kleines Python-Programm, das auf dem ESP2090 läuft und mit dem Microtronic über dessen Ein- und Ausgänge spricht. Du schreibst es im Editor der Weboberfläche, speicherst es im Ordner `userscripts` auf dem ESP und startest es mit **Run** (und beendest es mit **Stop**). Ein Neuflashen der Firmware ist dafür nie nötig.

Welche Funktionen ein Userscript benutzen kann (`setOutputs`, `getInputs`, `beep`, `log`, `tasteG` …), steht in der [Beschreibung der Firmware](../firmware/README.md).

## Wer sendet wohin?

Die Namen in den Userscripts sind aus Sicht des ESP gewählt:

| im Userscript | am 2090 | Richtung | auf dem 2090 |
|---|---|---|---|
| `setOutputs(wert)`, `out_1` … `out_4` | Eingänge 1–4 | ESP → 2090 | `DIN Rx` liest den Wert |
| `getInputs()`, `in_1` … `in_4` | Ausgänge 1–4 | 2090 → ESP | `DOT Rx` gibt den Wert aus |

Wert 1 ist jeweils Ein- bzw. Ausgang 1, Wert 8 Ein- bzw. Ausgang 4. Die originalen Klemmen des 2090 bleiben dabei nutzbar: Die Eingänge sind mit den Signalen des ESP verODERt, die Ausgänge werden für den ESP nur mitgelesen.

## Protokolle: Nibbles und Zeit

Zwischen den beiden laufen nur 4 Bit in jede Richtung, und keiner kann dem anderen „Bescheid sagen“, außer über genau diese Leitungen. Damit trotzdem nichts verloren geht, verabreden das Programm im 2090 und das Userscript eine Reihenfolge – ein **Protokoll**. Zwei Muster reichen für sehr vieles:

**1. Nur in eine Richtung.** Einer legt einen Wert an, der andere schaut regelmäßig nach. Damit das klappt, muss der Wert lange genug anliegen. Das Userscript schaut in den Beispielen alle 5 ms nach, der 2090 braucht für einen Befehl etwa 9,3 ms (mit eingeschalteter Anzeige länger). Ein Wert, den der 2090 für vier oder fünf Befehle stehen lässt, kommt also sicher an. Umgekehrt sollte das Userscript einen Wert so lange halten, bis der 2090 ihn gelesen hat – oder deutlich länger, als die Leseschleife im 2090 braucht.

**2. Anfrage und Antwort (Handshake).** Der 2090 stellt eine Frage (z. B. Ausgang 1 an), das Userscript antwortet auf den Eingängen und wartet, bis der 2090 „fertig“ meldet (Ausgänge wieder 0). Erst dann räumt es seine Antwort weg. So spielt es keine Rolle, wie schnell der eine oder der andere gerade ist.

Ein paar Hinweise aus der Praxis:

- **Nicht auf feste Zeiten bauen.** Mit eingeschalteter Anzeige ist der 2090 langsamer, und auch der ESP hat nebenbei zu tun (Webserver). Lieber warten, bis sich etwas ändert, als eine bestimmte Zeit abzuzählen. Feste Zeiten braucht nur die [LED-Matrix](LED-Matrix.md), die deshalb in der Firmware eingebaut ist.
- **Ruhezustand 0.** Wenn alle Ausgänge auf 0 stehen, „sagt niemand etwas“. Wer einen Wert gesendet hat, setzt am Ende wieder 0.
- **Matrix und Userscript nicht gleichzeitig an denselben Leitungen.** Die LED-Matrix benutzt Eingang 1 (Anfrage) und alle vier Ausgänge. Wer die Matrix eingeschaltet hat („LED on“), sollte kein Userscript laufen lassen, das ebenfalls darauf hört oder Eingang 1 setzt.

## Regeln für Userscripts

Userscripts laufen neben Webserver und Matrix auf demselben kleinen Prozessor. Damit alle drankommen, muss jedes Script die Kontrolle regelmäßig abgeben:

- In jeder Schleife `await asyncio.sleep_ms(...)` verwenden, nie `time.sleep`.
- Kein `input()`.

Vor dem Start prüft der ESP das Script und startet es nicht, wenn eine `while`- oder `for`-Schleife kein `await` enthält (Ausnahme: `for ... in range(n)` mit einer festen Zahl bis 64). Beim Speichern erscheint schon eine Warnung. Nach dem Ende oder bei **Stop** werden die Ausgänge auf 0 gesetzt und ein Ton beendet.

## Beispiele

Zu jedem Beispiel gehört ein Programm für den 2090 (`.mic`, ausführlich kommentiert, zum Hochladen mit **Upload**) und ein Userscript (`.py`). Die Programme sind kurz genug, um sie auch von Hand einzutippen.

**So startest du ein Beispiel:** Den Inhalt der `.py`-Datei in den Editor der Weboberfläche kopieren, unter einem Namen speichern (z. B. `ton.py`) und mit **Run** starten. Dann das Programm zum 2090 übertragen und dort starten. Die Matrix muss dabei aus sein.

### Lauflicht – nur der ESP

[firmware/userscripts/beispiel_lauflicht.py](../firmware/userscripts/beispiel_lauflicht.py) liegt schon auf dem ESP. Es schaltet die Eingänge des 2090 im Halbsekundentakt nacheinander ein (Wert 1, 2, 4, 8). Gut zum Ausprobieren, ob alles verbunden ist. Sichtbar wird es mit drei Befehlen auf dem 2090, die die Eingänge laufend anzeigen:

```
00  FD0  DIN R0
01  F10  DISP 1,R0
02  C00  GOTO 00
```

### Ton – der 2090 als Klavier (eine Richtung: 2090 → ESP)

[program/ton](../program/ton): Die Tasten 1–F am 2090 spielen eine C-Dur-Tonleiter über zwei Oktaven auf dem Buzzer des ESP2090.

- **2090** (10 Befehle): wartet mit `KIN` auf eine Taste, zeigt sie an, legt sie mit `DOT` auf die Ausgänge, lässt sie vier `NOP` lang stehen und setzt die Ausgänge wieder auf 0.
- **Userscript:** schaut alle 5 ms auf die Ausgänge des 2090. Bei jedem neuen Wert ungleich 0 spielt es 300 ms lang den passenden Ton.

```python
TOENE = [0, 262, 294, 330, 349, 392, 440, 494,
         523, 587, 659, 698, 784, 880, 988, 1047]
alt = 0
while True:
    wert = getInputs()
    if wert != alt:
        if wert != 0:
            beep(TOENE[wert], 300)
        alt = wert
    await asyncio.sleep_ms(5)
```

Weil der 2090 nach jedem Ton wieder 0 ausgibt, klingt auch dieselbe Taste zweimal hintereinander zweimal.

### Web-Taster – Zähler mit G und H (eine Richtung: ESP → 2090)

[program/webtaster](../program/webtaster): Die Tasten **Key G** und **Key H** der Weboberfläche (oder Leertaste und H auf der Tastatur) zählen auf dem 2090 hoch und herunter.

- **Userscript:** legt G auf Eingang 1 und H auf Eingang 2, solange die Taste gedrückt ist (in der Weboberfläche 0,5 s).
- **2090** (16 Befehle): liest die Eingänge mit `DIN`, zählt bei Eingang 1 hoch, bei Eingang 2 herunter und wartet dann, bis keine Taste mehr anliegt – sonst würde er während der halben Sekunde ständig weiterzählen.

```python
while True:
    wert = 0
    if tasteG["pressed"]:
        wert = wert | 1
    if tasteH["pressed"]:
        wert = wert | 2
    setOutputs(wert)
    await asyncio.sleep_ms(20)
```

### Zufallszahl – Anfrage und Antwort (beide Richtungen)

[program/zufallszahl](../program/zufallszahl): Jede Taste am 2090 holt eine echte Zufallszahl 0–F vom ESP und zeigt sie an. Der ESP32 hat einen Zufallsgenerator in Hardware – ein Zufall, der deutlich zufälliger ist als der des 2090.

Das Protokoll ist ein Handshake:

1. **2090:** Ausgang 1 an (Anfrage).
2. **ESP:** legt die Zahl auf die Eingänge 1–4.
3. **2090:** wartet ein paar Befehle, liest die Zahl mit `DIN`.
4. **2090:** Ausgänge auf 0 (fertig) – erst dann setzt der ESP die Eingänge wieder auf 0.

```python
import os
while True:
    if getInputs() == 1:                    # Anfrage vom 2090
        zahl = os.urandom(1)[0] & 15
        setOutputs(zahl)                    # Antwort
        while getInputs() != 0:             # warten, bis der 2090 fertig ist
            await asyncio.sleep_ms(5)
        setOutputs(0)
    await asyncio.sleep_ms(5)
```

Auf diesem Muster lässt sich vieles aufbauen: Messwerte von einem Sensor, die Uhrzeit aus dem Internet, ein zweites Nibble für größere Zahlen (einfach zweimal fragen) …
