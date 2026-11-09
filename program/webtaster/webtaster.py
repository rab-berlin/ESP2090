# Web-Taster fuer den 2090 (gehoert zu webtaster.mic)
#
# Die Tasten "Key G" und "Key H" der Weboberflaeche (auch Leertaste und H
# auf der Tastatur) werden an den 2090 weitergereicht:
# G -> Eingang 1, H -> Eingang 2, solange die Taste gedrueckt ist.

log("Web-Taster: G = Eingang 1, H = Eingang 2")
while True:
    wert = 0
    if tasteG["pressed"]:
        wert = wert | 1
    if tasteH["pressed"]:
        wert = wert | 2
    setOutputs(wert)
    await asyncio.sleep_ms(20)
