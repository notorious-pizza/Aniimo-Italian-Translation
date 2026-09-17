"""Verifica terminologica mirata sulle varianti trovate nell'audit a campione."""
import csv
import re
from collections import Counter

REPO = __import__("pathlib").Path(__file__).resolve().parents[1]
rows = []
with open(REPO / "data" / "translation_it.csv", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        rows.append(row)

def count(pattern: str, flags=re.IGNORECASE) -> tuple[int, list]:
    rx = re.compile(pattern, flags)
    hits = [(r["key"], r["it"][:110]) for r in rows if rx.search(r["it"])]
    return len(hits), hits

for name, pat in [
    ("Dipartimento Arti da Battaglia", r"Dipartimento Arti da Battaglia"),
    ("Dipartimento Arte della Battaglia", r"Dipartimento Arte della Battaglia"),
    ("Battle Art Department EN nell'IT (non tradotto)", r"Battle Art Department"),
    ("Shelly masc 'lo Shelly'", r"\blo Shelly\b"),
    ("Shelly fem 'la Shelly'", r"\bla Shelly\b"),
    ("Muyu residuo", r"Muyu"),
    ("Fragrancier", r"Fragrancier"),
    ("lo adorano / lo amano (elisione)", r"\blo (ador|ama|ama\b)"),
]:
    n, hits = count(pat)
    print(f"{name}: {n}")
    for k, t in hits[:6]:
        print(f"   [{k}] {t}")
