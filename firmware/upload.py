# Upload zum 2090: .mic-Datei einlesen und Bit fuer Bit ueber die Eingaenge
# des 2090 uebertragen (wie das Kassetteninterface 2095, am 2090 PGM 1).
import time

from hw import out_1, out_2, out_3
from core import log, setOutputs


delay_bit_us = 10000
delay_after_value_us = 10000

def clock_signal(pin, delay_us):
    pin.value(1)
    time.sleep_us(delay_us // 2)
    pin.value(0)
    time.sleep_us(delay_us // 2)

def load_instruction_to_busch2090(instr):

    for y in range(3):

        mask = 1

        for z in range(4):

            out_1.value(1 if (int(instr[y], 16) & mask) else 0)

            if y == 0 and z == 0:
                out_3.value(1)
                time.sleep_us(delay_bit_us)
            else:
                clock_signal(out_2, delay_bit_us)

            mask <<= 1

    setOutputs(0)
    time.sleep_us(delay_after_value_us)

def is_valid(instr):
    return len(instr) == 3 and all(c in "0123456789ABCDEF" for c in instr)

MIC_MAX_STEPS = 256     # Programmspeicher des 2090

def mic_instructions(text):
    """Befehle aus dem Text einer .mic-Datei: erste 3 Zeichen jeder Zeile,
    I/L -> 1, O/Q -> 0, nur gueltige Hex-Befehle. Gleiche Regeln wie
    micInstructions() in index.html."""
    if text.startswith("\ufeff"):
        text = text[1:]                                   # BOM
    out = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip().upper()
        if len(line) < 3:
            continue
        instr = (line[0:3]
            .replace("I", "1")
            .replace("L", "1")
            .replace("O", "0")
            .replace("Q", "0"))
        if is_valid(instr):
            out.append(instr)
    return out

def multipart_file(body, content_type, field="file"):
    """Inhalt des Formularfelds `field` aus multipart/form-data, sonst None."""
    i = content_type.find("boundary=")
    if i < 0:
        return None
    boundary = content_type[i + 9:].split(";")[0].strip().strip('"')
    if not boundary:
        return None
    marker = b'; name="' + field.encode() + b'"'
    for part in body.split(b"--" + boundary.encode()):
        head_end = part.find(b"\r\n\r\n")
        if head_end < 0 or marker not in part[:head_end]:
            continue
        data = part[head_end + 4:]
        if data.endswith(b"\r\n"):
            data = data[:-2]                              # Zeilenende vor der naechsten Grenze
        return data
    return None

def send_busch_instructions(instructions):
    log("MIC upload started ({} instructions)".format(len(instructions)))
    try:
        for instr in instructions:
            load_instruction_to_busch2090(instr)
    except Exception as e:
        log("MIC upload error: " + str(e))
    setOutputs(0)
    log("MIC upload finished")


def parse_request(body, ctype):
    """Befehle aus der Anfrage: (liste, None) oder (None, (text, status))."""
    # Formular aus dem Browser (multipart/form-data, Feld "file") oder die Datei
    # direkt als Body (z. B. curl --data-binary @prog.mic -H "Content-Type: text/plain").
    if ctype.startswith("multipart/form-data"):
        data = multipart_file(body, ctype)
        if data is None:
            return None, ("No MIC file in upload", 400)
    else:
        data = body

    try:
        text = data.decode()
    except UnicodeError:
        return None, ("MIC file is not a text file", 400)

    instr = mic_instructions(text)
    if not instr:
        return None, ("No valid instructions in MIC file", 400)
    if len(instr) > MIC_MAX_STEPS:
        return None, ("Too many instructions ({}), the 2090 has {} program steps".format(
            len(instr), MIC_MAX_STEPS), 400)
    return instr, None
