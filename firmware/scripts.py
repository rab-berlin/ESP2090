# Userscripts: Pruefung vor dem Start, Ausfuehren als Task, Stop,
# Fehlermeldung mit Zeilennummer.
import uasyncio as asyncio
import gc

from hw import out_1, out_2, out_3, out_4, in_1, in_2, in_3, in_4
from core import (log, exception_text, setOutputs, getInputs, waitInputs,
                  tasteG, tasteH, beep, stop_sound)
from matrix import setColors, setPalette, np

current_task = None

def is_running():
    return bool(current_task and not current_task.done())

# ================= SCRIPT-PRUEFUNG =================
# Vor dem Start (und als Warnung beim Speichern): Scripts laufen als Task im
# selben Event-Loop wie Webserver und Matrix. Eine Schleife ohne await haelt
# alles an und laesst sich nicht stoppen. Regeln:
#   - jede while-/for-Schleife braucht ein await im Rumpf;
#     ausgenommen for ... in range(n) mit fester Zahl n <= FOR_RANGE_MAX
#   - kein time.sleep / sleep_ms / sleep_us (blockiert), kein input()
# Grenze: geprueft wird, ob ein await im Rumpf steht, nicht ob es ausgefuehrt wird.
FOR_RANGE_MAX = 64

def _code_lines(code):
    """Zeilen ohne Kommentare und ohne Inhalt von Zeichenketten (Zeilen bleiben gleich)."""
    out, cur = [], []
    i, n = 0, len(code)
    quote = None                     # aktuelles Anfuehrungszeichen (' " \'\'\' \"\"\")
    while i < n:
        c = code[i]
        if quote:
            if c == "\\":
                if code[i + 1:i + 2] == "\n":      # Zeilenfortsetzung in der Zeichenkette
                    out.append("".join(cur))
                    cur = []
                i += 2
                continue
            if code.startswith(quote, i):
                cur.append(quote)
                i += len(quote)
                quote = None
                continue
            if c == "\n":
                out.append("".join(cur))
                cur = []
            i += 1
            continue
        if c == "#":
            while i < n and code[i] != "\n":
                i += 1
            continue
        if c in "'\"":
            quote = c * 3 if code.startswith(c * 3, i) else c
            cur.append(quote)
            i += len(quote)
            continue
        if c == "\n":
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out

def _is_name_char(c):
    return c.isalpha() or c.isdigit() or c == "_"

def _find_word(s, w, start=0):
    """Position von w als ganzes Wort in s, sonst -1."""
    i = s.find(w, start)
    while i >= 0:
        before = s[i - 1] if i > 0 else " "
        after = s[i + len(w)] if i + len(w) < len(s) else " "
        if not _is_name_char(before) and not _is_name_char(after):
            return i
        i = s.find(w, i + 1)
    return -1

def _indent(line):
    return len(line) - len(line.lstrip())

def _small_range(header):
    """True bei 'for x in range(...)' mit festen Zahlen und hoechstens FOR_RANGE_MAX Durchlaeufen."""
    i = header.find(" in ")
    if i < 0:
        return False
    rest = header[i + 4:].strip()
    if not rest.startswith("range(") or rest.find(")") < 0:
        return False
    args = rest[6:rest.find(")")]
    try:
        nums = [int(a) for a in args.split(",")]
        if not 1 <= len(nums) <= 3:
            return False
        return len(range(*nums)) <= FOR_RANGE_MAX
    except Exception:
        return False

def _header_colon(text):
    """Position des Doppelpunkts, der den Schleifenkopf beendet (ausserhalb von Klammern)."""
    depth = 0
    for i, c in enumerate(text):
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and depth == 0:
            return i
    return -1

def script_problem(code):
    """Erstes Problem als Text ("line N: ..."), sonst None."""
    lines = _code_lines(code)
    for no, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        for mod in ("time.", "utime."):
            p = text.find(mod + "sleep")
            if p >= 0 and (p == 0 or not _is_name_char(text[p - 1])):
                return "line {}: time.sleep blocks everything - use await asyncio.sleep_ms(...)".format(no + 1)
        if _find_word(text, "input") >= 0 and text[_find_word(text, "input") + 5:].lstrip().startswith("("):
            return "line {}: input() is not available".format(no + 1)

        kind = None
        if text.startswith("while") and not _is_name_char(text[5:6] or " "):
            kind = "while"
        elif text.startswith("for") and not _is_name_char(text[3:4] or " "):
            kind = "for"
        if not kind:
            continue
        colon = _header_colon(text)
        if colon < 0:
            continue        # kein Schleifenkopf, z. B. "for" in einem mehrzeiligen Listen-Ausdruck
        header = text[:colon]
        if kind == "for" and _small_range(header):
            continue
        # Rumpf: Rest der Zeile nach dem Doppelpunkt + alle tiefer eingerueckten Zeilen
        body = [text[colon + 1:]]
        ind = _indent(line)
        for nxt in lines[no + 1:]:
            if not nxt.strip():
                continue
            if _indent(nxt) <= ind:
                break
            body.append(nxt)
        if not any(_find_word(b, "await") >= 0 for b in body):
            what = "while loop" if kind == "while" else \
                "for loop (more than {} passes or not a fixed range)".format(FOR_RANGE_MAX)
            return "line {}: {} without await - add e.g. await asyncio.sleep_ms(20)".format(no + 1, what)
    return None

# ================= USER SCRIPT =================

USER_LINE_OFFSET = 3     # Zeilen vor dem Script in run_user_script (Leerzeile, import, async def)

def _traceback_text(e):
    try:
        from sys import print_exception       # MicroPython
        import io
        buf = io.StringIO()
        print_exception(e, buf)
        return buf.getvalue()
    except ImportError:
        import traceback                      # CPython (Simulation)
        return "".join(traceback.format_exception(type(e), e, e.__traceback__))
def script_error_line(e):
    """Zeile im Userscript (wie im Editor), in der der Fehler auftrat, sonst None."""
    line = None
    if isinstance(e, SyntaxError) and getattr(e, "lineno", None):
        line = e.lineno
    else:
        tb = _traceback_text(e)
        mark = '"<string>", line '
        p = tb.rfind(mark)
        if p >= 0:
            digits = ""
            for c in tb[p + len(mark):]:
                if not c.isdigit():
                    break
                digits += c
            if digits:
                line = int(digits)
    if line is None:
        return None
    line -= USER_LINE_OFFSET
    return line if line >= 1 else None

def indent(txt,n):
    return "\n".join(" "*n + line for line in txt.split("\n"))

async def run_user_script(code):
    global current_task

    try:

        wrapped=f"""
import uasyncio as asyncio
async def __user_task():
{indent(code,4)}
"""

        ns={
            "out_1":out_1,"out_2":out_2,"out_3":out_3,"out_4":out_4,
            "in_1":in_1,"in_2":in_2,"in_3":in_3,"in_4":in_4,
            "setOutputs":setOutputs,
            "getInputs": getInputs,
            "waitInputs": waitInputs,
            "tasteG":tasteG,
            "tasteH":tasteH,
            "log":log,
            "beep":beep,
            "setColors":setColors,
            "setPalette":setPalette,
            "np":np
        }

        exec(wrapped,ns)

        current_task=asyncio.create_task(ns["__user_task"]())
        log("User script started")

        await current_task

    except asyncio.CancelledError:
        log("User script stopped")

    except Exception as e:
        line = script_error_line(e)
        if line:
            line = min(line, code.count("\n") + 1)   # Syntaxfehler am Dateiende (z. B. offene Klammer)
        log("ERROR " + ("line {}: ".format(line) if line else "") + exception_text(e))

    setOutputs(0)   # auch nach normalem Ende oder Fehler
    gc.collect()

def stop_user_script():
    """Laufendes Userscript abbrechen, Ausgaenge 0, Ton aus. True, wenn eins lief."""
    global current_task
    if current_task:
        current_task.cancel()
        current_task=None
        setOutputs(0)
        stop_sound()
        return True
    return False
