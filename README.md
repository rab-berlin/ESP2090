# Bring deinen Busch Microtronic 2090 ins 21. Jahrhundert!

![ESP2090-Studio](/pics/ESP2090_Baustein_oben.jpg)

Das ESP2090-Studio verbindet den klassischen Lerncomputer Busch Microtronic 2090 mit einem modernen ESP32. ESP2090 erweitert den Microtronic um flexible, programmierbare Peripherie.

Der Grundgedanke ist einfach: Der Microtronic bleibt das originale 4-Bit-System – das ESP2090-Studio sorgt dafür, dass er plötzlich Dinge kann, die er ursprünglich nie konnte, ohne ihn selbst zu ersetzen. Wir verbinden dafür die Ein- und Ausgänge des Microtronic mit einem [ESP32](https://de.wikipedia.org/wiki/ESP32), auf dem [MicroPython](https://micropython.org) läuft. So können benutzerdefinierte Python-Programme über festgelegte Funktionen und Protokolle mit dem Microtronic interagieren. 

Vom einfachen Blinklicht über anpassbaren Zufallszahlengenerator, 2095-Tape-Emulator, Tongenerator, beliebige Sensoren, Internet-Anbindung bis hin zu einem 8x8-Matrix-LED-"Bildschirm" für den Microtronic - über die Weboberfläche des ESP2090-Studios lässt sich alles konfigurieren und steuern. 

![Webscreen](/pics/ESP2090_Desktop.jpg)


## Materialliste (BOM)

| Menge | Artikel | Preis (04/26) | Bemerkung |
| ---: | :--- | ---: | :--- |
| 1 | ESP32-C3 SuperMini | 1,70 | |
| 1 | SN74HCT244 8-fach Treiber | 2,60 | (10 St.) |
| 1 | CD4071 4-fach Oder-Gatter | 1,70 | (10 St.) |
| 2 | 4ch-2way-Levelshifter | 1,70 | (10 St., richtige Bauform beachten) |
| 1 | Buzzer, passiv | 1,50 | (10 St.) |
| 4 | Widerstand 470 Ohm | 2,00 | (Sortiment Widerstände 300 St.) |
| 4 | Widerstand 10k Ohm | - | (s.o.) |
| 1 | Widerstand 220 Ohm | - | (s.o.) |
| 1 | Widerstand 100 Ohm | - | (s.o.) |
| 2 | Kondensator 100 nF | 2,30 | (Sortiment Kondensatoren 300 St.) |
| 1 | Pfostenleiste 2,54 mm | 1,80 | (Sortiment male + female 20 St., benötigt male: 1 x 5, 1 x 3) |
| 1 | Buchsenleiste 2,54 mm | - | (s.o., benötigt female: 2 x 8 für ESP32) |
| 1 | IC-Sockel 14-polig | 2,20 | (Sortiment 66 St., für CD4071)
| 1 | IC-Sockel 20-polig | - | (s.o., für 74HCT244) |
| 18 | Metallösen 2,5 mm Innendurchmesser | 1,80 | (Sortiment 100 St., Stichwort: rivet, eyelet) |
| 1 | [Platine (PCB)](https://github.com/rab-berlin/ESP2090/tree/main/gerbers) | 9,00 | (5 St. aus Fernost - oder von mir, falls noch da) |
| 1 | WS2812B-LED-Matrix 8x8 | 1,80 | |
| 1 | Netzteil 5V 3A USB-C | 3,30 | |

Die Preise sind von AliExpress. Wer das alles frisch ordert, kommt ohne Platine für etwa 20 Euro weg - und hat danach noch viele Ersatzteile übrig. Ich bin aber sicher, dass du das meiste sowieso schon vorrätig hast. Lediglich den ESP, die Metallösen, die Platine und wahrscheinlich die LED-Matrix musst du wohl bestellen.

Du kannst natürlich auch ohne IC-Sockel und Buchsenleisten alles direkt auf die Platine löten. Ich persönlich hab´s aber lieber flexibel - versuch mal, einen falsch eingelöteten oder nicht funktionierenden IC wieder auszulöten...

Wer es richtig schön will, druckt sich noch einen passenden Busch-Bauteilträger dazu aus. ~~Daran arbeite ich noch...~~ [SCAD-](https://github.com/rab-berlin/ESP2090/blob/main/3d/ESP2090_mit_Zapfen.scad) und STL-Datei. Zur Befestigung der Platine am Träger brauchst du vier winzige Schrauben M2 und passende Muttern.


## Warum nur, warum?

Für den Test von neu geschriebenen oder geänderten Programmen habe ich zunächst den prima [Emulator von Michael Wessel](https://github.com/lambdamikel/Busch-2090) verwendet. Am PC entwickelt, auf SD-Karte geschrieben, in den Emulator umgestöpselt und übertragen... Haltnextnullnullrun...

Als ich dann auch mal auf dem "echten" Microtronic testen wollte, stieß ich - unter anderem - auf den Unterschied zwischen zufälligem und nicht so zufälligem Zufall. Also ergaben sich neue Notwendigkeiten:

- mehr auf dem originalen Busch Microtronic 2090 testen
- besondere Peripherie für meine Programme anschließen

Daher habe ich dann einen Raspberry Pi Zero W eingesetzt. Ein Python-Skript und ein paar Kabel mit Levelshifter übernahmen die Funktion des 2095-Kassetteninterfaces, und so konnte ich meine Ideen relativ schnell und unkompliziert über WLAN auf den Pi und von dort auf den Original-2090 bringen.

Für einige dieser neuen Programme wiederum benötigte ich manchmal auch Peripherie am Microtronic, die ich nicht immer mit Busch-Baukästen umsetzen konnte (oder wollte). Das erledigte zuerst ein Arduino Nano mit entsprechendem C-Programm, anschließend übernahm der Pi auch diese Aufgabe.

Der Raspberry Pi (also auch der von mir verwendete Zero) ist im Prinzip ein vollwertiger Computer mit Linux-Betriebssystem. Damit konnte ich natürlich alle Peripherie-Aufgaben bequem erledigen, und der Pi wäre auch eine bestens geeignete Hardware-Grundlage für alle weiteren Vorhaben gewesen. Irgendwie störte mich aber der Gedanke, dass zwischen dem Microtronic und dem Pi ein so großes _intellektuelles Gefälle_ herrschte. Ich wollte stattdessen, dass sich zwei Microcontroller "auf Augenhöhe" miteinander unterhalten - wenn auch mit 45 Jahren Altersunterschied. 

Was mich außerdem störte, ist die Preisentwicklung bei der Raspberry Pi Foundation. Es fing mal an als Experimentiercomputer zu einem Preis, den sich jeder lernwillige Einsteiger leisten konnte. Inzwischen werden teilweise Preise von 200 Euro für einen ausgebauten Pi aufgerufen. Obwohl es sicher gute Gründe dafür geben mag, ist das (für mich) nicht mehr unterstützenswert.

Die Leitidee sollte sein: Mit so wenig wie möglich so viel wie möglich erreichen. 

Meine Wahl fiel dann auf den ESP32 - nicht zuletzt, weil ich den Vorgänger ESP8266 in der Arduino-Umgebung schon öfter benutzt hatte. Der erste Gedanke war dann auch, dem ESP alles, was er wissen muss, in C beizubringen, um als idealer peripherer Begleiter für den Microtronic zu dienen. Einige gedankliche Iterationen später war die Frage dann aber: Wäre es nicht noch schöner, wenn man zur Laufzeit neue Ideen testen könnte, ohne die Firmware über die Arduino-IDE jeweils neu programmieren und flashen zu müssen? Wenn man also beliebige User-Skripte zur Laufzeit direkt aufrufen und ausführen könnte? 

C und Arduino-IDE fielen damit raus. Python rückte ins Zentrum, weil es zur Laufzeit interpretiert wird, und der Microtronic sowieso kein Geschwindigkeitsmonster ist. Genauer gesagt, die Wahl fiel auf MicroPython - womit die Ideen letztlich alle umsetzbar schienen. Und außerdem wollte ich mal wieder was neues lernen.

Entsprechend der Leitidee _Reduce to the max_ sollte es dann der ESP32-C3-Supermini sein, da dieser nur ca. 2 Euro kostet und genug GPIOs bietet für alle Ein- und Ausgänge des Microtronic sowie für ein bisschen zusätzliche Funktionen. 

## Schaltung

Die [Schaltung des ESP2090-Studios](https://github.com/rab-berlin/ESP2090/blob/main/documents/ESP2090.pdf) ist verhältnismäßig einfach. 

Der ESP32 arbeitet mit 3,3 Volt Betriebsspannung, der Microtronic hingegen mit 5 Volt (genauer gesagt: sogar 5,7 Volt - nachmessen!). Daher sind in den Signalwegen jeweils Levelshifter eingebaut. Da wir es mit verhältnismäßig langsamen Signalen im Bereich von Millisekunden zu tun haben, muss man über die Schaltgeschwindigkeit der Levelshifter nicht besonders intensiv nachdenken. Billige Teile aus China funktionieren gut.

Ich habe darauf geachtet, dass die Ein- und Ausgänge des Microtronic elektrisch vom ESP entkoppelt sind, das heißt, sie sollten auch bei gleichzeitigem Anschluss des ESP2090-Studios nach wie vor nutzbar bleiben, falls z.B. weitere Peripherie aus dem Busch-Sortiment verwendet wird. Für diese Entkopplung werden zwei ICs eingesetzt, ein CD4071 und ein 74HCT244.

### Eingänge

Jeder Eingang des Microtronic ist an je einen Ausgang eines ODER-Gatters (CD4071) angeschlossen. Je ein Eingang eines ODER-Gatters ist mit einem GPIO des ESP32 verbunden, der andere Eingang des Gatters ist "frei" (kann also wie bisher als Eingang des 2090 genutzt werden). So können weiterhin beliebige Peripherie-Schaltungen an den Microtronic angeschlossen werden - ohne dass es zu elektrischer Beeinflussung durch den ESP32 kommt. 

Die Eingänge des 4071 sind extrem hochohmig, über Ströme muss man sich also keine Gedanken machen.

### Ausgänge 

Jeder Ausgang des Microtronic ist an je zwei Eingänge eines 74HCT244 angeschlossen. Dadurch wird ein Microtronic-Ausgang praktisch "verdoppelt" - eine Ausgangskopie bleibt unabhängig nutzbar, daran kann also wie bisher beliebige (Busch-)Peripherie angeschlossen werden. Die andere Ausgangskopie ist mit einem GPIO des ESP verbunden. Dadurch kann das ESP2090-Studio alle Veränderungen an den Ausgängen des Microtronic überwachen, ohne eventuell angeschlossene andere Peripherie elektrisch zu stören. 

Es ist zu beachten, dass der 74HCT244 maximal 20 mA an seinen Ausgängen liefert. Mehr sollte man auch dem Microtronic niemals abverlangt haben, wenn man seine Ausgänge nicht überlasten wollte - laut Anleitungsbuch 2. Teil, S. 41: "maximal 15 mA". Wer mehr will oder braucht, steuert mit dem Ausgang wie üblich erstmal einen Transistor an.

## Was kann ich damit machen?

Die einfache Antwort: alles. 

Prinzipiell brauchst du nur ein passendes Python-Script auf dem ESP2090, welches auf die Signale an den vier Ausgängen des Microtronic passend reagiert und - falls nötig - die richtigen Signale zur gewünschten Zeit an die Eingänge des Microtronic sendet. 

Die ernüchternde Antwort: natürlich nicht alles, weil der Programmspeicher des Microtronic eben doch nur 256 Befehle umfasst. Und die Anzahl der Register mit 16 (plus 16 Speicherregister) auch recht begrenzt ist.

Der Spaß liegt wie immer darin, mit diesen Einschränkungen eben doch etwas zu schaffen, das "sinnvoll" und funktional ist.

### Protokolle 

Wenn du bisher noch nie etwas mit Protokollen zu tun haben wolltest (hast du aber, weil du gerade im Internet unterwegs bist) - jetzt solltest du damit anfangen, wenn du dem Microtronic die _Welt der Dinge_ zugänglich machen willst.

Als einfaches Beispiel für ein Protokoll dient der "Bildschirm". Um alle 8x8 Pixel der LED-Matrix anzusteuern, werden die Speicherregister 0-F des Microtronic nacheinander auf die Ausgänge gelegt - also 16 Nibbles, insgesamt 64 Bit. Damit dies zu genau festgelegten Zeiten passiert, sendet das ESP2090-Studio zuerst einen Request (REQ), wartet auf eine Bestätigung (ACK) und liest dann alle 9 Millisekunden die Ausgänge - denn bei deaktivierter Anzeige benötigt der 2090 ziemlich genau 9 ms für die Ausführung einer Instruktion.

Auf diese Weise können auch andere Protokolle zum Datenaustausch zwischen Microtronic und ESP32 realisiert werden. 

## Beispiele

### Microtronic goes Hollywood

...


### [BerlinUhr2090](https://github.com/rab-berlin/BerlinUhr2090)

### [Life2090](https://github.com/rab-berlin/Life2090)

