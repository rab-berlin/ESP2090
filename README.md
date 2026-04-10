# Bring deinen Busch Microtronic 2090 ins 21. Jahrhundert!

![Prototyp](/pics/IMG_20260410_195403.jpg)

Wir schließen an die Ein- und Ausgänge des Microtronic 2090 einen [ESP32](https://de.wikipedia.org/wiki/ESP32) an, auf dem [MicroPython](https://micropython.org) läuft. Dadurch können wir beliebige Python-Programme laufen lassen, die mit dem 2090 kommunizieren. 

Vom einfachen Blinklicht über anpassbaren Zufallszahlengenerator, 2095-Tape-Emulator, Tongenerator, beliebige Sensoren, Internet-Anbindung bis hin zu einem 8x8-Matrix-LED-"Bildschirm" für den Microtronic - über die Weboberfläche lässt sich alles konfigurieren und steuern. 

![Webscreen](/pics/IMG_20260403_173029.jpg)

## Warum nur, warum?

Für den Test von neu geschriebenen oder geänderten Programmen habe ich zunächst den prima [Emulator von Michael Wessel](https://github.com/lambdamikel/Busch-2090) verwendet. Am PC entwickelt, auf SD-Karte geschrieben, in den Emulator umgestöpselt und übertragen... Haltnextnullnullrun...

Als ich dann auch mal auf dem "echten" Microtronic testen wollte, stieß ich - unter anderem - auf den Unterschied zwischen zufälligem und nicht so zufälligem Zufall. Also ergaben sich neue Notwendigkeiten:

- mehr auf dem originalen Busch Microtronic 2090 testen
- besondere Peripherie für meine Programme anschließen

Daher habe ich dann einen Raspberry Pi Zero W eingesetzt. Ein Python-Skript und ein paar Kabel mit Levelshifter übernahmen die Funktion des 2095-Kassetteninterfaces, und so konnte ich meine Ideen relativ schnell und unkompliziert über WLAN auf den Pi und von dort auf den Original-2090 bringen.

Für einige dieser neuen Programme wiederum benötigte ich manchmal auch Peripherie am Microtronic, die ich nicht immer mit Busch-Baukästen umsetzen konnte (oder wollte). Das erledigte zuerst ein Arduino Nano mit entsprechendem C-Programm, anschließend übernahm der Pi auch diese Aufgabe.

Der Raspberry Pi (also auch der von mir verwendete Zero) ist im Prinzip ein vollwertiger Computer mit Linux-Betriebssystem. Damit konnte ich natürlich alle Peripherie-Aufgaben bequem erledigen, und der Pi wäre auch eine bestens geeignete Hardware-Grundlage für alle weiteren Vorhaben gewesen. Irgendwie störte mich aber der Gedanke, dass zwischen dem Microtronic und dem Pi ein so großes Gefälle herrschte. Ich wollte, dass sich zwei Microcontroller miteinander "auf Augenhöhe" unterhalten - wenn auch mit lächerlichen 45 Jahren Altersunterschied. 

Was mich außerdem störte, ist die Preisentwicklung bei der Raspberry Pi Foundation. Es fing mal an als Experimentiercomputer zu einem Preis, den sich jeder lernwillige Einsteiger leisten konnte. Inzwischen werden teilweise Preise von 200 Euro für einen Pi aufgerufen. Obwohl es sicher gute Gründe dafür geben mag, ist das (für mich) nicht mehr unterstützenswert.

Die Leitidee sollte sein: Mit so wenig wie möglich so viel wie möglich erreichen. 

Meine Wahl fiel dann auf den ESP32 - nicht zuletzt, weil ich vorher schon öfter den Vorgänger ESP8266 in der Arduino-Umgebung benutzt habe. Der erste Gedanke war dann auch, dem ESP alles, was er wissen muss, in C beizubringen, um als idealer peripherer Begleiter für den Microtronic zu dienen. Einige gedankliche Iterationen später war die Frage dann aber: Wäre es nicht noch schöner, wenn man zur Laufzeit neue Ideen testen könnte, ohne die Firmware über die Arduino-IDE jeweils neu programmieren und flashen zu müssen? Wenn man also beliebige User-Skripte zur Laufzeit direkt aufrufen und ausführen könnte? 

C und Arduino-IDE fielen damit raus. Python rückte ins Zentrum, weil es zur Laufzeit interpretiert wird, und der Microtronic sowieso kein Geschwindigkeitsmonster ist. Genauer gesagt, die Wahl fiel auf MicroPython - womit die Ideen letztlich alle umsetzbar schienen. Und außerdem wollte ich mal wieder was neues lernen.

Entsprechend der Leitidee _Reduce to the max_ sollte es dann der ESP32-C3-Supermini sein, da dieser zum einen nur ca. 1 Euro kostet und zum anderen genug GPIOs für alle Ein- und Ausgänge des Microtronic sowie für ein bisschen zusätzliche Funktionen bietet. 

## Schaltung

Die [Schaltung des ESP2090-Studios](https://github.com/rab-berlin/ESP2090/blob/main/documents/ESP2090.pdf) ist verhältnismäßig einfach. 

Der ESP32 arbeitet mit 3,3 Volt Betriebsspannung, der Microtronic hingegen mit 5 Volt (genauer gesagt: sogar 5,7 Volt - nachmessen!). Daher sind in den Signalwegen jeweils Levelshifter eingebaut. Da wir es mit verhältnismäßig langsamen Signalen im Bereich von Millisekunden zu tun haben, muss man über die Schaltgeschwindigkeit der Levelshifter nicht besonders intensiv nachdenken. Billige Teile aus China funktionieren gut.

Ich habe darauf geachtet, dass die Ein- und Ausgänge des Microtronic elektrisch vom ESP entkoppelt sind, das heißt, sie sollten auch bei gleichzeitigem Anschluss des ESP2090-Studios nach wie vor nutzbar bleiben, falls z.B. weitere Peripherie aus dem Busch-Sortiment verwendet wird.

### Eingänge

Die Eingänge des Microtronic sind an je einen Ausgang eines ODER-Gatters (CD4071) angeschlossen. Je ein Eingang eines ODER-Gatters ist mit einem GPIO des ESP32 verbunden, der andere Eingang des Gatters ist "frei" (kann also wie bisher als Eingang des 2090 genutzt werden). So können weiterhin beliebige Peripherie-Schaltungen an den Microtronic angeschlossen werden - ohne dass es zu elektrischer Beeinflussung durch den ESP32 kommt. Die Eingänge des 4071 sind extrem hochohmig, über Ströme muss man sich also keine Gedanken machen.

### Ausgänge 

Die Ausgänge des Microtronic sind an je zwei Eingänge eines 74HCT244 angeschlossen. Dadurch wird ein Microtronic-Ausgang praktisch "verdoppelt" - ein Ausgang bleibt unabhängig nutzbar, kann also beliebige Peripherie ansteuern. Der andere Ausgang ist mit einem GPIO verbunden, sodass der ESP32 alle Veränderungen an den Ausgängen überwachen kann, ohne eventuell angeschlossene weitere Peripherie elektrisch zu stören. Es ist zu beachten, dass der 74HCT244 maximal 20 mA an seinen Ausgängen liefert - mehr sollte auch der Microtronic im Laufe seines Lebens (45 Jahre) niemals geliefert haben, wenn man seine Ausgänge nicht überlasten wollte. Für die Ansteuerung eines Transistors ist das mehr als ausreichend.

## Was kann ich damit machen?

Die einfache Antwort: alles. 

Prinzipiell brauchst du nur ein passendes Python-Script auf der ESP-Seite, welches auf die Signale an den vier Ausgängen des Microtronic passend reagiert und - falls nötig - die richtigen Signale zur gewünschten Zeit an die Eingänge des Microtronic sendet. 

Die ernüchternde Antwort: natürlich nicht alles, weil der Programmspeicher des 2090 eben doch nur 256 Befehle umfasst. Und die Anzahl der Register mit 16 (plus 16 Speicherregister) auch recht begrenzt ist.

Der Spaß liegt wie immer darin, mit diesen Einschränkungen eben doch etwas zu schaffen, das "sinnvoll" und funktional ist.

### Protokolle 

Wenn du bisher noch nie etwas mit Protokollen zu tun haben wolltest (hast du aber, weil du gerade im Internet unterwegs bist) - jetzt solltest du damit anfangen, wenn du dem Microtronic die _Welt der Dinge_ zugänglich machen willst.

Als einfaches Beispiel für ein Protokoll dient der "Bildschirm". Um alle 8x8 Pixel der LED-Matrix anzusteuern, werden die Speicherregister 0-F des Microtronic nacheinander auf die Ausgänge gelegt - also insgesamt 16 Nibbles, 64 Bit. Damit dies zu genau festgelegten Zeiten passiert, sendet der ESP zuerst einen Request (REQ), wartet auf eine Bestätigung (ACK) und liest dann alle 9 Millisekunden die Ausgänge - denn bei deaktivierter Anzeige benötigt der 2090 ziemlich genau 9 ms für die Ausführung einer Instruktion.

Auf diese Weise können auch andere Protokolle zum Datenaustausch zwischen Microtronic und ESP32 realisiert werden. 

## Beispiele

### [Berlin-Uhr](https://de.wikipedia.org/wiki/Berlin-Uhr)

Der Uhrmacher und Elektroingenieur [Dieter Binninger](https://de.wikipedia.org/wiki/Dieter_Binninger) hat 1975 die erste Uhr der Welt, die die Zeit mit leuchtenden farbigen Feldern anzeigt, mitten auf dem Kurfürstendamm in Berlin aufstellen lassen. Viele kannten diese Uhr unter dem Namen _Mengenlehre-Uhr_, obwohl sie mit der damals im Schulunterricht noch sehr kritisch gesehenen Mengenlehre gar nichts zu tun hat. Und die wenigsten haben verstanden, wie man auf dieser Uhr die Zeit ablesen soll. Trotzdem ist sie ein Wahrzeichen (gewesen). Auch heute noch ist die [Berlin-Uhr](https://de.wikipedia.org/wiki/Berlin-Uhr) zu bestaunen, wenn auch an einem deutlich weniger prominenten Standort.

Es gab in den Berliner Souvenirläden auch ein Tischmodell dieser Uhr zu kaufen - und darin arbeitet ein [TMS1000](https://de.wikipedia.org/wiki/Texas_Instruments_TMS1000) von Texas Instruments. Welcher Chip in der Original-Uhr arbeitet, ist mir leider nicht bekannt. Aber 1975 war die Auswahl an Microcontrollern gar nicht so groß, also darf spekuliert werden... In jedem Fall schließt sich hier der Kreis, da der größere Bruder TMS1600 im Microtronic immer noch zuverlässig seine Dienste verrichtet.

![Berlinuhr](/pics/IMG_20260403_221740.jpg)

Der Microtronic kann jetzt auch Berlin-Uhr! Wer kann die richtige Uhrzeit erkennen? 

Das [Berlin-Uhr-Microtronic-Programm](https://github.com/rab-berlin/ESP2090/blob/main/program/berlinuhr/berlin.mic) dazu ist einfach. 

Alles, was auf der LED-Matrix angezeigt werden soll, befindet sich in den Speicherregistern 0-F. Ein gesetztes Bit bedeutet, dass die entsprechende LED leuchet, ein nicht gesetztes Bit lässt die LED ausgeschaltet. Im Unterprogramm _Frame_ werden die Werte in den Speicherregistern schnell hintereinander auf die Ausgänge gelegt. Der ESP liest diese Werte und steuert die LED-Matrix entsprechend. Für ein genaues Timing gibt es noch ein REQ-Signal vom ESP und ein ACK-Signal vom Microtronic.

```
Frame      DIN REQ-ACK-CLEAR           Auf REQ warten
           ANDI #1,REQ-ACK-CLEAR       .
           BRZ Frame                   .
           DOT REQ-ACK-CLEAR           ACK senden
           EXRL                        Speicherregister 0-7 in Arbeitsregister holen
           DOT r0                      Alle Register 0-F als Nibble senden
           DOT r1                      .
           DOT r2                      .
           ...                         .
           DOT rF                      .
           EXRL                        Speicherregister 0-7 wieder zurück
           MOVI #0,REQ-ACK-CLEAR       Null auf Ausgänge legen
           DOT REQ-ACK-CLEAR           .
           RET	
```

Standard ist übrigens, dass alle LEDs nur rot leuchten. Man kann dem ESP2090-Studio über ein User-Skript [farbmatrix.py](https://github.com/rab-berlin/ESP2090/blob/main/program/berlinuhr/farbmatrix.py) allerdings vorher mitteilen, welche Farbe jede einzelne LED der Matrix annehmen soll, wenn sie eingeschaltet wird. Dann wird's schön bunt.

Im Hauptprogramm wird die Zeit mit TIME aktualisiert, dementsprechend die einzelnen Speicherregister mit Werten gefüllt und schließlich das Unterprogramm aufgerufen, um den Frame zu übermitteln. 

Ohne ESP2090-Studio und LED-Matrix wirkt das Programm allerdings (optisch) wenig anprechend: Das Display wird abgeschaltet und danach passiert nix mehr, weil der Microtronic genauso verzweifelt wie vergeblich auf das REQ-Signal wartet. 

Wer's ohne ESP2090-Studio prinzipiell mal testen will, muss einen Taster korrekt am Eingang 1 anschließen und kann dann verfolgen, wie der Microtronic bei jedem Tastendruck einen Frame über die Ausgänge sendet.

### Microtronic goes Hollywood

...

### [Game of Life](https://de.wikipedia.org/wiki/Conways_Spiel_des_Lebens)

...
