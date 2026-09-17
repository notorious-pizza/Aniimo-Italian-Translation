"""Audit fase 2a — copertura e pairing della traduzione vs gioco locale (solo lettura).

1. Estrae l'inglese reale dal gioco (LuaScripts.xdf -> NewTextMap_en + Compress_en)
2. Confronta le chiavi CSV vs chiavi di gioco
3. Verifica il fingerprint di build dichiarato nel manifest
4. Verifica il pairing per chiave: sha256(inglese di gioco) == source_sha256 del CSV
5. Rileva non-tradotte (it == en) e vuote
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GAME = Path(r"D:\Program Files (x86)\Steam\steamapps\common\Aniimo")
XDF = GAME / r"Aniimo_Data\cvs\res\lua\LuaScripts.xdf"

sys.path.insert(0, str(REPO / "tools"))
import aniimo_it_installer as inst  # noqa: E402

OUT = REPO / ".audit"
OUT.mkdir(exist_ok=True)

# --- 1. inglese dal gioco -------------------------------------------------
with zipfile.ZipFile(XDF) as zf:
    names = zf.namelist()
    i18n_names = [n for n in names if "I18N" in n]
    mapping, records, _prefix = inst.load_language(zf, "en")

game_en = {r["key"]: r["text"] for r in records}
print(f"file I18N nell'archivio: {len(i18n_names)}")
for n in i18n_names[:20]:
    print("  ", n)

# --- 2. CSV ---------------------------------------------------------------
csv_rows: list[dict] = []
with open(REPO / "data" / "translation_it.csv", encoding="utf-8", newline="") as f:
    for row in csv.DictReader(f):
        csv_rows.append(row)
csv_map = {r["key"]: r for r in csv_rows}

game_keys = set(game_en)
csv_keys = set(csv_map)
print(f"\nchiavi gioco (en): {len(game_keys)}")
print(f"righe CSV:          {len(csv_rows)} (chiavi uniche: {len(csv_keys)})")

missing = sorted(game_keys - csv_keys, key=lambda k: int(k) if k.isdigit() else 0)
extra = sorted(csv_keys - game_keys, key=lambda k: int(k) if k.isdigit() else 0)
print(f"mancanti nel CSV (presenti nel gioco): {len(missing)}")
print(f"extra nel CSV (assenti dal gioco):     {len(extra)}")

# --- 3. fingerprint di build ---------------------------------------------
manifest = json.loads((REPO / "data" / "supported_versions.json").read_text(encoding="utf-8"))
fp_game = inst.sha256_keys(list(game_keys))
declared = manifest["known_source_key_sha256"]
print(f"\nfingerprint chiavi gioco:    {fp_game}")
print(f"fingerprint dichiarato:      {declared}")
print(f"fingerprint combacia:        {fp_game == declared}")

# --- 4. pairing per chiave ------------------------------------------------
pair_ok = pair_fail = 0
fail_examples: list[dict] = []
for key in game_keys & csv_keys:
    src_hash = hashlib.sha256(game_en[key].encode("utf-8")).hexdigest()
    if src_hash == csv_map[key]["source_sha256"]:
        pair_ok += 1
    else:
        pair_fail += 1
        if len(fail_examples) < 20:
            fail_examples.append(
                {"key": key, "en_gioco": game_en[key][:80], "csv_sha": csv_map[key]["source_sha256"]}
            )
print(f"\npairing sha256 per chiave: OK={pair_ok}  MISMATCH={pair_fail}")
for ex in fail_examples[:10]:
    print("  MISMATCH", ex["key"], repr(ex["en_gioco"]))

# --- 5. non tradotte / vuote ---------------------------------------------
same_as_en = [k for k in game_keys & csv_keys if csv_map[k]["it"] == game_en[k]]
empty_it = [k for k in game_keys & csv_keys if not csv_map[k]["it"].strip()]
print(f"\nitaliano identico all'inglese (probabili nomi propri): {len(same_as_en)}")
print(f"italiano vuoto:                                        {len(empty_it)}")

# classificazione grezza delle identiche per capire se legittime
def classify(t: str) -> str:
    if not t.strip():
        return "vuota"
    if len(t) <= 3:
        return "molto_corta(<=3)"
    if t.strip().isupper():
        return "maiuscolo"
    if " " not in t.strip() and len(t) <= 20:
        return "parola_unica"
    return "testo"

cls = Counter(classify(game_en[k]) for k in same_as_en)
print("composizione delle identiche:", dict(cls))

json.dump(
    {
        "i18n_files": i18n_names,
        "game_keys": len(game_keys),
        "csv_rows": len(csv_rows),
        "csv_keys": len(csv_keys),
        "missing_in_csv": missing[:200],
        "missing_count": len(missing),
        "extra_count": len(extra),
        "extra_keys": extra[:200],
        "fingerprint_match": fp_game == declared,
        "pair_ok": pair_ok,
        "pair_fail": pair_fail,
        "pair_fail_examples": fail_examples,
        "same_as_en_count": len(same_as_en),
        "same_as_en_class": dict(cls),
        "empty_it_count": len(empty_it),
        "empty_it_keys": empty_it[:200],
    },
    open(OUT / "coverage_report.json", "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=2,
)
print(f"\nreport -> {OUT / 'coverage_report.json'}")
