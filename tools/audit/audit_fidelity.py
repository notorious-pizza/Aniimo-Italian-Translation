"""Audit fase 2b — controlli automatici su TUTTE le stringhe + campione stratificato.

Controlli globali (112.187 stringhe):
- preservazione placeholder {0}/{1}/… (multiset)
- preservazione tag tipo <b></b>, <color=#…>, [/…] ecc.
- newline / spazi iniziali-finali
- rapporto di lunghezza sospetto (>3x o <1/3, con soglie)
- residui di inglese in stringhe italiane lunghe (euristica wordlist)
- stringhe identiche EN=IT lunghe (classificazione del perché)

Poi genera un campione stratificato (seed fisso) da far revisionare a mano.
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GAME = Path(r"D:\Program Files (x86)\Steam\steamapps\common\Aniimo")
XDF = GAME / r"Aniimo_Data\cvs\res\lua\LuaScripts.xdf"
OUT = REPO / ".audit"

sys.path.insert(0, str(REPO / "tools"))
import aniimo_it_installer as inst  # noqa: E402

# --- carica corpora ---------------------------------------------------------
with zipfile.ZipFile(XDF) as zf:
    _, records, _ = inst.load_language(zf, "en")
game_en = {r["key"]: r["text"] for r in records}

csv_map: dict[str, str] = {}
with open(REPO / "data" / "translation_it.csv", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        csv_map[row["key"]] = row["it"]

PLACEHOLDER = re.compile(r"\{\d+(?:[^{}]*)?\}")
TAG = re.compile(r"</?[A-Za-z][^<>]*>|\[/?[A-Za-z][^\[\]]*\]")
EN_WORDS = re.compile(
    r"\b(the|and|with|your|you|from|this|that|will|have|been|into|after|before|when|where|which|"
    r"their|there|about|would|could|should|damage|attack|defense|level|reward|quest|item|items|"
    r"required|available|complete|completed|failed|progress|select|click|open|close|enter|exit)\b",
    re.IGNORECASE,
)

issues: dict[str, list] = {k: [] for k in (
    "placeholder", "tag", "newline", "bordi", "lunghezza", "residuo_inglese"
)}
identici_lunghi: list[dict] = []

def register(cat: str, key: str, en: str, it: str, detail: str = "") -> None:
    if len(issues[cat]) < 4000:
        issues[cat].append({"key": key, "en": en[:160], "it": it[:160], "detail": detail})

for key, en in game_en.items():
    it = csv_map.get(key, "")
    if it == en:
        if len(en) > 40 and " " in en.strip() and not en.strip().isupper():
            if len(identici_lunghi) < 3000:
                identici_lunghi.append({"key": key, "en": en})
        continue
    ph_en = Counter(PLACEHOLDER.findall(en))
    ph_it = Counter(PLACEHOLDER.findall(it))
    if ph_en != ph_it and (ph_en or ph_it):
        register("placeholder", key, en, it, f"EN={dict(ph_en)} IT={dict(ph_it)}")
    tg_en = Counter(TAG.findall(en))
    tg_it = Counter(TAG.findall(it))
    if tg_en != tg_it and (tg_en or tg_it):
        register("tag", key, en, it, f"EN={dict(tg_en)} IT={dict(tg_it)}")
    if en.count("\n") != it.count("\n"):
        register("newline", key, en, it, f"\\n EN={en.count(chr(10))} IT={it.count(chr(10))}")
    if (en != en.strip()) or (it != it.strip() and not en.strip().startswith("|")):
        if (en.startswith(" ") != it.startswith(" ")) or (en.endswith(" ") != it.endswith(" ")):
            register("bordi", key, en, it, "spazio iniziale/finale diverso")
    len_en, len_it = len(en.strip()), len(it.strip())
    if len_en >= 25 and (len_it > len_en * 3 or len_it * 3 < len_en):
        register("lunghezza", key, en, it, f"EN={len_en} IT={len_it}")
    if len_it > 60:
        # residui inglesi: almeno 2 parole inglesi comuni distinte nella stringa IT
        found = sorted(set(m.group(0).lower() for m in EN_WORDS.finditer(it)))
        if len(found) >= 2:
            register("residuo_inglese", key, en, it, ",".join(found))

# --- campione stratificato --------------------------------------------------
rng = random.Random(20260917)
translated = [
    (k, en, csv_map[k]) for k, en in game_en.items() if csv_map.get(k) and csv_map[k] != en
]

def bucket(en: str) -> str:
    n = len(en)
    if n <= 25:
        return "A_ui_corta"
    if n <= 90:
        return "B_media"
    if n <= 250:
        return "C_dialogo"
    return "D_lunga"

by_bucket: dict[str, list] = {}
for item in translated:
    by_bucket.setdefault(bucket(item[1]), []).append(item)

SAMPLE_SIZES = {"A_ui_corta": 70, "B_media": 90, "C_dialogo": 70, "D_lunga": 40}
sample: list[dict] = []
for name, items in sorted(by_bucket.items()):
    take = rng.sample(items, min(SAMPLE_SIZES.get(name, 30), len(items)))
    for k, en, it in take:
        sample.append({"key": k, "bucket": name, "en": en, "it": it})

# campione extra: le "identiche lunghe" (sospette) e le segnalate automatiche
for e in rng.sample(identici_lunghi, min(60, len(identici_lunghi))):
    sample.append({"key": e["key"], "bucket": "E_identica_lunga", "en": e["en"], "it": csv_map[e["key"]]})

def sample_from(cat: str, n: int) -> None:
    pool = issues[cat]
    for e in rng.sample(pool, min(n, len(pool))):
        sample.append({"key": e["key"], "bucket": f"F_auto_{cat}", "en": e["en"], "it": e["it"], "detail": e.get("detail", "")})

for cat, n in (("placeholder", 25), ("tag", 15), ("residuo_inglese", 25), ("lunghezza", 15), ("newline", 10), ("bordi", 10)):
    sample_from(cat, n)

rng.shuffle(sample)

# --- report -----------------------------------------------------------------
stats = {
    "stringhe_totali": len(game_en),
    "tradotte_diverse": len(translated),
    "identiche_en_it": sum(1 for k in game_en if csv_map.get(k) == game_en[k]),
    "identiche_lunghe_sospette": len(identici_lunghi),
    "esiti_automatici": {c: len(v) for c, v in issues.items()},
    "campione_generato": len(sample),
}
print(json.dumps(stats, ensure_ascii=False, indent=2))

with open(OUT / "fidelity_auto_issues.json", "w", encoding="utf-8") as f:
    json.dump(issues, f, ensure_ascii=False, indent=2)
with open(OUT / "fidelity_sample.jsonl", "w", encoding="utf-8") as f:
    for s in sample:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
print("scritti: fidelity_auto_issues.json, fidelity_sample.jsonl")
