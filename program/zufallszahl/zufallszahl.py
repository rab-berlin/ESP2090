# Zufallszahl fuer den 2090 (gehoert zu zufallszahl.mic)
#
# Der 2090 fragt mit Ausgang 1 an. Das Script legt eine echte Zufallszahl
# 0-15 (aus dem Zufallsgenerator des ESP32) auf seine Eingaenge und
# wartet, bis der 2090 seine Ausgaenge wieder auf 0 setzt.
import os

log("Zufallszahl: bereit")
while True:
    if getInputs() == 1:                    # Anfrage vom 2090
        zahl = os.urandom(1)[0] & 15
        setOutputs(zahl)                    # Antwort auf Eingang 1-4
        log("Zufallszahl " + str(zahl))
        while getInputs() != 0:             # warten, bis der 2090 fertig ist
            await asyncio.sleep_ms(5)
        setOutputs(0)
    await asyncio.sleep_ms(5)
