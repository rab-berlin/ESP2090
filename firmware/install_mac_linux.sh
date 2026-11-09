#!/bin/sh
# ESP2090 Studio - Dateien per mpremote auf den ESP32-C3 kopieren
# Voraussetzung: MicroPython ist bereits geflasht (siehe ANLEITUNG.txt)
# und mpremote ist installiert:  pip install mpremote
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "Kopiere Programmdateien ..."
mpremote cp boot.py hw.py main.py matrix_draw.py basicweb.py microdot.py index.html webrepl_cfg.py :

echo "Lege Ordner userscripts an ..."
mpremote mkdir :userscripts 2>/dev/null || true
mpremote cp userscripts/beispiel_lauflicht.py :userscripts/beispiel_lauflicht.py

if [ -f "$DIR/wifi.json" ]; then
  echo "Kopiere wifi.json ..."
  mpremote cp "$DIR/wifi.json" :wifi.json
else
  echo "Keine wifi.json gefunden - der ESP startet im Einrichtungsmodus (WLAN 'ESP32-Setup')."
fi

echo "Neustart ..."
mpremote reset
echo "Fertig."
