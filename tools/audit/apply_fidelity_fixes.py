"""Applica le 3 correzioni emerse dall'audit di fedeltà del 2026-09-17.

- [1090869768] [2068081817]: allinea "Dipartimento Arte della Battaglia"
  alla forma dominante "Dipartimento Arti da Battaglia" (13 occorrenze)
- [1799612016]: allinea "La Shelly derubata" al maschile usato nelle altre
  14 occorrenze dello stesso NPC ("lo Shelly")

Formato preservato: senza BOM, CRLF, QUOTE_MINIMAL, colonna source_sha256 invariata.
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV_PATH = REPO / "data" / "translation_it.csv"

FIXES = {
    "1090869768": ("Dipartimento Arte della Battaglia", "Dipartimento Arti da Battaglia"),
    "2068081817": ("Dipartimento Arte della Battaglia", "Dipartimento Arti da Battaglia"),
    "1799612016": ("La Shelly derubata", "Lo Shelly derubato"),
}

with open(CSV_PATH, encoding="utf-8", newline="") as f:
    reader = csv.reader(f)
    rows = list(reader)

header = rows[0]
kcol, itcol = header.index("key"), header.index("it")
applied = 0
for row in rows[1:]:
    key = row[kcol]
    if key in FIXES:
        old, new = FIXES[key]
        if old in row[itcol]:
            row[itcol] = row[itcol].replace(old, new)
            applied += 1
            print(f"[{key}] {old!r} -> {new!r}")
        else:
            print(f"[{key}] ATTENZIONE: pattern {old!r} non trovato in: {row[itcol][:120]!r}")

with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerows(rows)
print(f"\nCorrezioni applicate: {applied}/{len(FIXES)}")
