# Beispiel-Userscript: Lauflicht auf den vier Ausgaengen
# Wird in der Weboberflaeche mit "Run" gestartet und mit "Stop" beendet.
# Wichtig: In jeder Schleife "await asyncio.sleep_ms(...)" verwenden,
# sonst laesst sich das Script nicht stoppen.

log("Beispiel: Lauflicht gestartet")
i = 0
while True:
    setOutputs(1 << i)
    i = (i + 1) % 4
    await asyncio.sleep_ms(500)
