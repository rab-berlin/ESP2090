import uasyncio as asyncio

color_matrix = [
    ["rot","rot","rot","rot","rot","rot","rot","rot"],
    ["schwarz","schwarz","schwarz","schwarz","schwarz","schwarz","schwarz","schwarz"],
    ["rot","rot","rot","rot","rot","rot","rot","rot"],
    ["schwarz","schwarz","schwarz","schwarz","schwarz","schwarz","schwarz","schwarz"],
    ["orange","orange","rot","orange","orange","schwarz","schwarz","blau"],
    ["orange","orange","rot","orange","orange","rot","schwarz","schwarz"],
    ["schwarz","schwarz","schwarz","schwarz","schwarz","schwarz","schwarz","schwarz"],
    ["orange","orange","orange","orange","orange","orange","orange","orange"],
]

# seit Firmware v1.4 erwartet setColors 64 Namen, oberste Zeile zuerst
setColors([farbe for zeile in color_matrix for farbe in zeile])
