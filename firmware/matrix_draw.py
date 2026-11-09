# Zeichenlogik der LED-Matrix (Matrix-Protokoll v2)
#
# Wird von main.py benutzt, nachdem die Nibbles eines Befehls gelesen sind.
# Enthaelt keine Hardware-Zugriffe und kein Timing, damit sie auch auf dem
# PC getestet werden kann.
#
# Zwei Ebenen mit je 64 Eintraegen, Index = y * 8 + x (x = Spalte, y = Zeile):
#   bits   - Bitebene: 1 = Pixel an
#   colors - Farbebene: Nummer in PALETTE
# Sichtbar ist: Bit an -> Farbe aus der Farbebene.
#
# Befehle (ACK, Datennibbles):
#   1  16 Nibbles   Bild in die Bitebene
#   3  a            ganze Matrix, Zeichenart a (0-3)
#   4  x, y         Cursor 1 / Punkt
#   6  x, y         Cursor 2 / Rechteck gefuellt
#   7  x, y         Cursor 2 / Rechteck als Rahmen
#   8  x, y         Cursor 2 / Linie, danach Cursor 1 = Cursor 2
#   10 k, w         Nibble k der Bitebene = w
#   11 r            schieben: 0 links, 1 rechts, 2 hoch, 3 runter (+8 mit Umlauf)
#   13 w            Stapel: Bit 0 Farbmatrix, Bit 1 Bitmatrix; Bit 2-3 Aktion:
#                   +0 push, +4 pop, +8 peek (zurueckholen, bleibt auf dem Stapel),
#                   +12 Stapel leeren. Je Matrix ein Stapel mit STACK_MAX Plaetzen,
#                   bei vollem Stapel faellt beim Push die aelteste Sicherung heraus.
#                   Keine Aktion baut die Anzeige neu auf: sichtbar mit dem naechsten
#                   Neuaufbau.
#   14 f            aktive Farbe
#   15 -            Schlafmodus (ohne Nibble, in main.py): REQ bleibt aus, bis der 2090
#                   F auf die Ausgaenge legt. Die Anzeige bleibt stehen.
# Zeichenart aus den beiden +8-Bits (x +8 -> Bit 0, y +8 -> Bit 1):
#   0 nur Farbebene, 1 Farbe + Bits (Farbe 0 = Bit aus), 2 nur Bits an, 3 nur Bits aus

ROWS = 8
COLS = 8
N = ROWS * COLS

PALETTE_DEFAULT = (
    (0, 0, 0),      # 0 schwarz
    (10, 0, 0),     # 1 rot (Vorgabe)
    (10, 4, 0),     # 2 orange
    (10, 10, 0),    # 3 gelb
    (0, 8, 0),      # 4 gruen
    (0, 8, 6),      # 5 tuerkis
    (0, 0, 10),     # 6 blau
    (6, 0, 10),     # 7 violett
    (10, 0, 6),     # 8 magenta
    (10, 10, 10),   # 9 weiss
    (3, 0, 0),      # 10 dunkelrot
    (0, 3, 0),      # 11 dunkelgruen
    (0, 0, 3),      # 12 dunkelblau
    (3, 3, 0),      # 13 oliv
    (10, 3, 3),     # 14 rosa
    (3, 3, 3),      # 15 grau
)

COLOR_NAMES = {
    "schwarz": 0, "rot": 1, "orange": 2, "gelb": 3, "gruen": 4, "tuerkis": 5,
    "blau": 6, "violett": 7, "magenta": 8, "weiss": 9,
}

# Anzahl der Datennibbles je ACK (0 = Code ohne Bedeutung)
NIBBLES = (0, 16, 0, 1, 2, 0, 2, 2, 2, 0, 2, 1, 0, 1, 1, 0)

OFF = (0, 0, 0)

STACK_MAX = 8                       # Plaetze je Stapel (ACK 13)


class Matrix:
    def __init__(self):
        self.palette = list(PALETTE_DEFAULT)
        self.bits = bytearray(N)
        self.colors = bytearray([1] * N)    # alles rot
        self.c1x = self.c1y = 0
        self.c2x = self.c2y = 0
        self.paint = 1
        self.stack_bits = []                # ACK 13: Stapel der Bitmatrix
        self.stack_colors = []              # ACK 13: Stapel der Farbmatrix

    # ---------- Grundoperation ----------
    def _apply(self, i, art):
        if art == 0:
            self.colors[i] = self.paint
        elif art == 1:
            self.colors[i] = self.paint
            self.bits[i] = 1 if self.paint else 0
        elif art == 2:
            self.bits[i] = 1
        else:
            self.bits[i] = 0

    # ---------- Formen ----------
    def _point(self, x, y, art):
        self._apply(y * COLS + x, art)

    def _rect(self, art, filled):
        x0, x1 = min(self.c1x, self.c2x), max(self.c1x, self.c2x)
        y0, y1 = min(self.c1y, self.c2y), max(self.c1y, self.c2y)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if filled or x == x0 or x == x1 or y == y0 or y == y1:
                    self._apply(y * COLS + x, art)

    def _line(self, art):
        x, y = self.c1x, self.c1y
        x1, y1 = self.c2x, self.c2y
        dx, dy = abs(x1 - x), -abs(y1 - y)
        sx = 1 if x < x1 else -1
        sy = 1 if y < y1 else -1
        err = dx + dy
        while True:
            self._apply(y * COLS + x, art)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def _shift(self, r):
        d, wrap = r & 3, r & 8
        nb, nc = bytearray(N), bytearray(self.colors)
        for y in range(ROWS):
            for x in range(COLS):
                sx, sy = x, y
                if d == 0:
                    sx = x + 1          # nach links: Pixel kommt von rechts
                elif d == 1:
                    sx = x - 1
                elif d == 2:
                    sy = y - 1          # nach oben: Pixel kommt von unten
                else:
                    sy = y + 1
                if wrap:
                    sx %= COLS
                    sy %= ROWS
                elif not (0 <= sx < COLS and 0 <= sy < ROWS):
                    continue            # frei werdende Stelle: Bit aus, Farbe bleibt
                j = sy * COLS + sx
                nb[y * COLS + x] = self.bits[j]
                nc[y * COLS + x] = self.colors[j]
        self.bits, self.colors = nb, nc

    # ---------- Befehle ----------
    def frame(self, nibbles):
        """ACK 1: 16 Nibbles in die Bitebene (Nibble k = Zeile k // 2)."""
        b = self.bits
        idx = 0
        for v in nibbles:
            b[idx] = v & 1
            b[idx + 1] = (v >> 1) & 1
            b[idx + 2] = (v >> 2) & 1
            b[idx + 3] = (v >> 3) & 1
            idx += 4
        return True

    def command(self, ack, data):
        """Fuehrt einen Befehl aus. Liefert True, wenn die Anzeige neu
        aufgebaut werden muss."""
        if ack == 1:
            return self.frame(data)
        if ack in (4, 6, 7, 8):
            x, y = data[0], data[1]
            art = ((x >> 3) & 1) | (((y >> 3) & 1) << 1)
            x &= 7
            y &= 7
            if ack == 4:
                self.c1x, self.c1y = x, y
                self._point(x, y, art)
            else:
                self.c2x, self.c2y = x, y
                if ack == 8:
                    self._line(art)
                    self.c1x, self.c1y = x, y
                else:
                    self._rect(art, ack == 6)
            return art != 0
        if ack == 3:
            art = data[0] & 3
            for i in range(N):
                self._apply(i, art)
            return art != 0
        if ack == 10:
            k, w = data[0], data[1]
            i = 4 * k
            for j in range(4):
                self.bits[i + j] = (w >> j) & 1
            return True
        if ack == 11:
            self._shift(data[0])
            return True
        if ack == 13:
            return self._stack(data[0])
        if ack == 14:
            self.paint = data[0] & 15
            return False
        return False

    def _stack(self, w):
        """ACK 13: push (+0), pop (+4), peek (+8), leeren (+12) fuer Farbmatrix (1) und/oder Bitmatrix (2).
        Baut die Anzeige nicht neu auf (Rueckgabe immer False)."""
        aktion = w >> 2
        for bit in (1, 2):
            if not w & bit:
                continue
            stapel = self.stack_colors if bit == 1 else self.stack_bits
            if aktion == 0:
                if len(stapel) >= STACK_MAX:
                    stapel.pop(0)
                stapel.append(bytearray(self.colors if bit == 1 else self.bits))
            elif aktion == 3:
                del stapel[:]
            elif stapel:
                oben = stapel.pop() if aktion == 1 else stapel[-1]
                if bit == 1:
                    self.colors = bytearray(oben)
                else:
                    self.bits = bytearray(oben)
        return False

    # ---------- Anzeige ----------
    def render(self, np):
        """Schreibt beide Ebenen in den LED-Puffer (Verdrahtung: np[x * 8 + y])."""
        pal, bits, cols = self.palette, self.bits, self.colors
        for y in range(ROWS):
            for x in range(COLS):
                i = y * COLS + x
                np[x * ROWS + y] = pal[cols[i]] if bits[i] else OFF

    # ---------- fuer User-Scripts ----------
    def set_colors(self, names):
        """64 Farbnamen, oberste Zeile zuerst (wie bisher setColors)."""
        if len(names) != N:
            return False
        for r in range(ROWS):
            for c in range(COLS):
                name = names[(ROWS - 1 - r) * COLS + c]
                self.colors[r * COLS + c] = COLOR_NAMES.get(name, 0)
        return True

    def set_palette(self, index, rgb):
        if 0 <= index < 16:
            self.palette[index] = tuple(int(v) & 255 for v in rgb)
            return True
        return False
