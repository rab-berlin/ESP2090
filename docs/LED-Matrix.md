# Die LED-Matrix als Bildschirm für den Microtronic

Die 8x8-LED-Matrix ist ein Sonderfall der Kommunikation über die Ein- und Ausgänge: Der Microtronic schickt Daten über seine vier Ausgänge, das ESP2090-Studio liest sie und zeichnet. Im Unterschied zu den [Userscripts](Userscripts.md) ist das Protokoll fest in die Firmware eingebaut. Auf dem 2090 läuft dafür eine besondere Senderoutine, auf dem ESP muss nur die Matrix eingeschaltet sein (**„LED on“** in der Weboberfläche). Was die Matrix zeigt, erscheint auch live in der Weboberfläche.

Es gibt zwei Arten, die Matrix zu benutzen, und beide lassen sich in einem Programm mischen:

- **Blockmodus:** Der 2090 schickt ein ganzes Bild: 16 Register mit je 4 Bit = 64 Pixel. So arbeitet z. B. die [BerlinUhr](../program/berlinuhr).
- **Zeichenmodus:** Der 2090 schickt kurze Befehle mit ein oder zwei Nibbles: Punkt, Rechteck, Rahmen, Linie, Farbe, Schieben … So kommt man mit wenigen Befehlen zu bunten Bildern und spart Register.

## Zwei Ebenen: Bitmatrix und Farbmatrix

Der ESP merkt sich das Bild in zwei Ebenen mit je 64 Einträgen:

- Die **Bitmatrix** sagt, **welche Pixel an sind** (1 Bit je Pixel).
- Die **Farbmatrix** sagt, **in welcher Farbe** ein Pixel leuchtet, wenn es an ist (eine der 16 Farben der Palette, siehe unten). Am Anfang ist sie überall rot.

Sichtbar ist: Pixel an → Farbe aus der Farbmatrix. Ist ein Pixel aus, ist es dunkel, egal welche Farbe für diese Stelle eingetragen ist.

![Bitmatrix und Farbmatrix ergeben die Anzeige](bilder/matrix-ebenen.svg)

Die Trennung ist praktisch: Die Farben legt man einmal fest (zum Beispiel Streifen wie oben, oder die Farben der BerlinUhr), danach schickt der 2090 nur noch, *welche* Pixel leuchten – die Farbe kommt automatisch mit. Umgekehrt kann man Farben ändern, ohne das Bild neu zu schicken.

Wer schreibt in welche Ebene?

| | Bitmatrix | Farbmatrix |
|---|---|---|
| Blockmodus (ganzes Bild) | ✓ | – |
| Zeichenmodus | je nach Zeichenart (siehe unten) | je nach Zeichenart |
| Userscript `setColors(...)` | – | ✓ |

## Wie die Übertragung abläuft

Der 2090 hat keinen Takt, den der ESP sehen könnte. Die beiden verabreden deshalb einen Startzeitpunkt, und danach zählt der ESP einfach mit: **Bei ausgeschalteter Anzeige (`DISOUT`) braucht der 2090 für jeden Befehl ziemlich genau 9,3 ms.**

1. **Anfrage (REQ):** Der ESP setzt Eingang 1 des 2090 auf 1. Ein ACK erkennt er erst, nachdem die Ausgänge des 2090 einmal auf 0 standen.
2. **Antwort (ACK):** Der 2090 wartet in einer Schleife auf REQ (`DIN`, `ANDI`, `BRZ`) und legt dann mit `DOT` eine Befehlsnummer 1–15 auf seine Ausgänge. Der ESP erkennt sie, liest nach 0,7 ms zur Kontrolle noch einmal und nimmt REQ zurück.

   Die Kontrolle ist nötig, weil der 2090 langsam ist: Ein `DOT` schaltet die vier Ausgänge nicht gleichzeitig, sondern nacheinander, der ganze Vorgang dauert etwa 166 µs. Im Bild wechseln die Ausgänge von 1110 auf 0000, Ausgang 2, 3 und 4 fallen jeweils gut 50 µs nacheinander. Würde der ESP den ersten Wert nehmen, den er sieht, bekäme er oft einen Zwischenwert. Nach 0,7 ms steht der Wert sicher.

   ![Der 2090 schaltet seine Ausgänge nacheinander (Logic-Analyzer)](bilder/2090-ausgaenge-nacheinander.jpg)
3. **Daten:** Danach gibt der 2090 in jedem Befehlsschritt ein Nibble mit `DOT` aus, im Blockmodus 16, im Zeichenmodus ein oder zwei. Der ESP liest jeweils in der Mitte des Schritts. Die genauen Zeiten stehen bei den beiden Modi.
4. **Ende:** Der 2090 setzt seine Ausgänge wieder auf 0. Erst danach erkennt der ESP das nächste ACK – ein Wert, der auf den Ausgängen liegen bleibt, wird also nicht doppelt gelesen.

Antwortet der 2090 nicht innerhalb von 30 ms, nimmt der ESP REQ zurück, wartet kurz und fragt erneut. So bleibt die Weboberfläche bedienbar, auch wenn auf dem 2090 gerade kein passendes Programm läuft.

**Wichtig:** Vor jeder Übertragung muss die Anzeige des 2090 mit `DISOUT` (`F02`) ausgeschaltet sein – nur dann stimmen die 9,3 ms. Wer zwischendurch etwas mit `DISP` anzeigt, schaltet sie vor dem nächsten ACK wieder aus. Am sichersten steht `DISOUT` am Anfang der Senderoutine.

## Blockmodus: ein ganzes Bild

Im Blockmodus schickt der 2090 nach ACK 1 den Inhalt von 16 Registern. Jedes Register stellt vier Pixel dar. Die Register füllen die Bitmatrix zeilenweise von unten nach oben, jede Zeile besteht aus zwei Registern: das gerade für die linke Hälfte, das ungerade für die rechte. Bit 0 (Wert 1) ist jeweils das linke Pixel der Hälfte.

![Welches Register welche Pixel darstellt](bilder/matrix-blockmodus-register.svg)

Die Farben kommen aus der Farbmatrix – der Blockmodus ändert sie nicht.

**Zeitablauf:** Zwischen ACK und dem ersten Register steht genau **ein** Befehl (meist `EXRL`, siehe unten). Das erste Register liest der ESP 23,4 ms nach dem ACK, die weiteren alle 9,2 ms.

![Zeitablauf im Blockmodus](bilder/matrix-blockmodus-zeit.svg)

**Senderoutine:** Weil der 2090 nur 16 Register hat und einige davon für das Programm selbst braucht, liegt die untere Hälfte des Bildes meist in den Speicherregistern 0–7. `EXRL` tauscht sie direkt vor dem Senden in die Register 0–7 und danach wieder zurück. Gleichzeitig ist `EXRL` genau der eine Befehl, der zwischen ACK und erstem Register stehen muss (so in `film_color` und der BerlinUhr):

```
bild: FD0  DIN R0        ┐ warten auf REQ
      310  ANDI 1,R0     │
      E..  BRZ bild      ┘
      FE0  DOT R0        ACK 1 (R0 ist hier 1)
      F0D  EXRL          Register 0-7 mit den Speicherregistern 0-7 tauschen
      FE0  DOT R0        Register 0: unterste Zeile, links
      FE1  DOT R1        Register 1: unterste Zeile, rechts
      ...
      FEF  DOT RF        Register F: oberste Zeile, rechts
      F0D  EXRL          zurücktauschen
      FE.  DOT R.        ein Register mit 0: Ausgänge auf 0
      F07  RET
```

## Zeichenmodus: Befehle mit Koordinaten

Im Zeichenmodus besteht ein Befehl aus dem ACK und ein oder zwei Nibbles:

| ACK | Nibbles | Wirkung |
|---|---|---|
| 3 | a | ganze Matrix in Zeichenart a (z. B. alles in der aktiven Farbe an, alles aus) |
| 4 | x, y | Cursor 1 setzen und Punkt zeichnen |
| 6 | x, y | Cursor 2 setzen, gefülltes Rechteck zwischen Cursor 1 und 2 |
| 7 | x, y | Cursor 2 setzen, Rechteck als Rahmen |
| 8 | x, y | Cursor 2 setzen, Linie; danach Cursor 1 = Cursor 2 (Linienzug) |
| 10 | k, w | die vier Pixel, die im Blockmodus Register k darstellt, auf w setzen |
| 11 | r | Bit- und Farbmatrix schieben: 0 links, 1 rechts, 2 hoch, 3 runter; +8 mit Umlauf |
| 14 | f | aktive Farbe 0–15 wählen (siehe Palette) |
| 15 | w | Anzeige: 1 umschalten, 2 an, 3 aus (gezeichnet wird weiter) |

ACK 2, 5, 9, 12 und 13 haben bisher keine Bedeutung und werden ignoriert. Hier kommen später weitere Zeichenbefehle dazu.

**Koordinaten:** x ist die Spalte (0 links bis 7 rechts), y die Zeile (0 unten bis 7 oben).

![Koordinaten im Zeichenmodus](bilder/matrix-zeichenmodus-koordinaten.svg)

**Zeichenart:** Eine Koordinate braucht nur 3 Bit. Das vierte Bit (Wert 8) von x und y legt fest, was in Bit- und Farbmatrix geschrieben wird:

| x +8 | y +8 | Zeichenart | Farbmatrix | Bitmatrix | wozu |
|---|---|---|---|---|---|
| – | – | 0 | aktive Farbe | bleibt | Cursor 1 setzen, ohne etwas zu zeigen; Farben vorbereiten, bevor die Pixel kommen |
| ✓ | – | 1 | aktive Farbe | an (bei Farbe 0 = schwarz: aus) | normales Zeichnen |
| – | ✓ | 2 | bleibt | an | einen Ausschnitt zeigen |
| ✓ | ✓ | 3 | bleibt | aus | einen Ausschnitt ausblenden |

Im Bild: `ACK 4` mit x = 1, y = 1 setzt Cursor 1, dann zeichnet `ACK 6` mit x = 4+8, y = 3 das gefüllte Rechteck in der aktiven Farbe. Die blaue Linie entsteht aus `ACK 4` (6, 0) und `ACK 8` (7+8, 4). Cursor 1 wird für eine Figur ohne +8 gesetzt (Zeichenart 0): So leuchtet vorher kein einzelnes Pixel auf, und die Figur bringt den Eckpunkt mit. Nur für einen einzelnen Punkt bekommt `ACK 4` selbst das +8.

Bei ACK 3 ist das Nibble direkt die Zeichenart: `ACK 3, 1` füllt die ganze Matrix in der aktiven Farbe, `ACK 3, 3` schaltet alle Pixel aus, ohne die Farben zu vergessen.

**Palette** (für ACK 14, Farbnummer f):

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| schwarz | rot | orange | gelb | grün | türkis | blau | violett |

| 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|
| magenta | weiß | dunkelrot | dunkelgrün | dunkelblau | oliv | rosa | grau |

Ein Userscript kann jede dieser Farben mit `setPalette(nummer, (r, g, b))` ändern.

**Zeitablauf:** Das erste Nibble kommt **direkt im nächsten Schritt** nach dem ACK. Der ESP liest es 14,2 ms nach dem ACK, das zweite 9,2 ms später.

![Zeitablauf im Zeichenmodus](bilder/matrix-zeichenmodus-zeit.svg)

**Senderoutine:** Eine einzige Routine genügt für alle Befehle. Das ACK steht in R1, die Nibbles in R2 und R3:

```
cmd:   F02  DISOUT        Anzeige aus (Pflicht)
warte: FD0  DIN R0        ┐ warten auf REQ
       310  ANDI 1,R0     │
       E..  BRZ warte     ┘
       FE1  DOT R1        ACK
       FE2  DOT R2        Nibble 1 (x bzw. Wert)
       FE3  DOT R3        Nibble 2 (y); bei Befehlen mit einem Nibble ohne Bedeutung
       100  MOVI 0,R0
       FE0  DOT R0        Ausgänge auf 0
       F07  RET
```

Für jeden Befehl gibt es dann einen kurzen Einsprung, der R1 setzt und zu `cmd` springt, zum Beispiel `punkt: 141 C..` (R1 = 4, `GOTO cmd`). Ein roter Punkt bei (3, 4) ist damit:

```
1E1  MOVI E,R1    ACK 14 = Farbe
112  MOVI 1,R2    Farbe 1 = rot
B..  CALL cmd
1B2  MOVI B,R2    x = 3 + 8 (Zeichenart 1: Farbe und Pixel an)
143  MOVI 4,R3    y = 4
B..  CALL punkt
```

## Farben aus einem Userscript

Statt mit ACK 14 und Zeichenart 0 kann man die Farbmatrix auch von einem Userscript aus füllen: `setColors(liste)` erwartet 64 Farbnamen, oberste Zeile zuerst (`"schwarz"`, `"rot"`, `"orange"`, `"gelb"`, `"gruen"`, `"tuerkis"`, `"blau"`, `"violett"`, `"magenta"`, `"weiss"`). So macht es die BerlinUhr mit [farbmatrix.py](../program/berlinuhr/farbmatrix.py): Das Script setzt einmal die Farben und endet, danach schickt der 2090 nur noch Bilder im Blockmodus.

## Beispiele

| Programm | Was es zeigt |
|---|---|
| [demo_matrix](../program/demo_matrix) | Vorführung aller Zeichenbefehle: Jede Taste am 2090 zeigt die nächste (ganze Matrix, Punkt, Rechteck, Rahmen, Ausschnitt aus- und einblenden, Linienzug, Schieben, Anzeige an/aus, Glitter, bunte Vielecke, Rahmen mit laufenden Farben, Regenbogen, Feuerwerk). 209 Befehle. |
| [film_color](../program/film_color) | Ein kleiner Film mit farbigen Pixeln: Bilder im Blockmodus, Farben im Zeichenmodus mit Zeichenart 0. Nutzt alle 256 Befehle. |
| [berlinuhr](../program/berlinuhr) | Die Berliner Mengenlehreuhr: Bilder im Blockmodus, Farben per Userscript. |

Die `.mic`-Dateien sind ausführlich kommentiert.

**So startest du ein Beispiel:** `.mic`-Datei mit **Upload** in der Weboberfläche zum 2090 übertragen, Programm auf dem 2090 starten, in der Weboberfläche **LED on** drücken.
