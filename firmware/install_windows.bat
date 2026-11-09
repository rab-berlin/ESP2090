@echo off
REM ESP2090 Studio - Dateien per mpremote auf den ESP32-C3 kopieren
REM Voraussetzung: MicroPython ist bereits geflasht (siehe ANLEITUNG.txt)
REM und mpremote ist installiert:  pip install mpremote

cd /d "%~dp0"

echo Kopiere Programmdateien ...
mpremote cp boot.py hw.py main.py matrix_draw.py basicweb.py microdot.py index.html webrepl_cfg.py :
if errorlevel 1 goto fehler

echo Lege Ordner userscripts an ...
mpremote mkdir :userscripts 2>nul
mpremote cp userscripts\beispiel_lauflicht.py :userscripts/beispiel_lauflicht.py

if exist "%~dp0wifi.json" (
  echo Kopiere wifi.json ...
  mpremote cp "%~dp0wifi.json" :wifi.json
) else (
  echo Keine wifi.json gefunden - der ESP startet im Einrichtungsmodus ^(WLAN "ESP32-Setup"^).
)

echo Neustart ...
mpremote reset
echo Fertig.
pause
goto :eof

:fehler
echo.
echo FEHLER: Verbindung zum ESP fehlgeschlagen. Ist Thonny noch verbunden? Dann Thonny schliessen.
pause
