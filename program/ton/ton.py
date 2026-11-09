# Ton fuer den 2090 (gehoert zu ton.mic)
#
# Der 2090 legt eine Tastennummer 1-15 auf seine Ausgaenge. Das Script
# spielt dazu einen Ton der C-Dur-Tonleiter auf dem Buzzer.

TOENE = [0, 262, 294, 330, 349, 392, 440, 494,      # 1-7: c' bis h'
         523, 587, 659, 698, 784, 880, 988, 1047]   # 8-15: c'' bis c'''

log("Ton: bereit")
alt = 0
while True:
    wert = getInputs()
    if wert != alt:
        if wert != 0:
            beep(TOENE[wert], 300)          # 300 ms lang
            log("Taste " + str(wert))
        alt = wert
    await asyncio.sleep_ms(5)
