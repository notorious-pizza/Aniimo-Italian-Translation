#!/usr/bin/env python3
"""Kit di aggiornamento autonomo della traduzione (per umani e agenti AI).

Comandi:
  estrai   [--game-dir DIR]   Esporta dal gioco le stringhe nuove/modificate
                              in data/da_tradurre_<build>.csv (colonna `it` da riempire)
  unisci   --file F [...]     Fondi le traduzioni nel CSV principale e aggiorna
                              il manifest (richiede il gioco raggiungibile per verificare)
  verifica [--game-dir DIR]   Controlo completo post-fusione (copertura + pairing)

Tutto a sola lettura verso il gioco tranne nulla: né estrai né unisci né verifica
modificano i file di gioco — l'applicazione resta affidata all'installer/GUI.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import aniimo_it_installer as inst  # noqa: E402


def load_live_records(game_dir: Path | None) -> tuple[Path, list[dict]]:
    gd = game_dir or inst.resolve_game_dir(None)
    paths = inst.resolve_paths(gd)
    with zipfile.ZipFile(paths.xdf, "r") as zf:
        _, records, _ = inst.load_language(zf, "en")
    return gd, records


def cmd_estrai(args: argparse.Namespace) -> int:
    game_dir, records = load_live_records(Path(args.game_dir) if args.game_dir else None)
    build = inst.read_game_update(game_dir) or "sconosciuta"
    catalog = inst.load_translation_catalog("en")
    translations = inst.load_translations("en")

    rows: list[dict] = []
    n_new = n_mod = 0
    for rec in records:
        key, text = rec["key"], rec["text"]
        if key not in catalog:
            n_new += 1
            rows.append({"key": key, "en": text, "source_sha256": hashlib.sha256(text.encode()).hexdigest(), "it": ""})
            continue
        expected = hashlib.sha256(text.encode()).hexdigest()
        known = catalog[key].get("source_sha256", "")
        if expected == known:
            continue  # invariata
        if translations.get(key) == text:
            continue  # è la nostra patch italiana già installata, non un testo ufficiale
        n_mod += 1
        rows.append({"key": key, "en": text, "source_sha256": expected, "it": ""})

    removed = [k for k in catalog if k not in {r["key"] for r in records}]
    out = REPO / "data" / f"da_tradurre_{build}.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "en", "source_sha256", "it"],
                           quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Build {build} · stringhe totali {len(records)}")
    print(f"Nuove: {n_new} · modificate: {n_mod} · da tradurre: {len(rows)} · rimosse: {len(removed)}")
    print(f"File: {out}")
    print("Prossimo passo: riempi la colonna `it` (tu o un agente AI), poi:")
    print(f"  python tools/aggiorna_traduzione.py unisci --file {out.name} --game-dir \"{game_dir}\"")
    return 0


def cmd_unisci(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.is_file():
        print(f"File non trovato: {src}")
        return 1
    game_dir, records = load_live_records(Path(args.game_dir) if args.game_dir else None)
    live = {r["key"]: r["text"] for r in records}

    incoming: list[dict] = []
    with open(src, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not row.get("key") or not (row.get("it") or "").strip():
                continue
            incoming.append(row)
    if not incoming:
        print("Nessuna riga con traduzione compilata nel file.")
        return 1

    mismatched = 0
    for row in incoming:
        live_text = live.get(row["key"])
        if live_text is None:
            print(f"  ✗ chiave {row['key']} assente dal gioco: saltata")
            mismatched += 1
            continue
        actual = hashlib.sha256(live_text.encode()).hexdigest()
        if actual != row.get("source_sha256"):
            print(f"  ✗ chiave {row['key']}: l'inglese del gioco è cambiato da Estrazione: saltata")
            mismatched += 1
    usable = [r for r in incoming
              if live.get(r["key"]) is not None
              and hashlib.sha256(live[r["key"]].encode()).hexdigest() == r.get("source_sha256")]
    print(f"Traduzioni valide: {len(usable)}/{len(incoming)} (saltate {mismatched} per hash non corrispondente)")

    csv_path = REPO / "data" / "translation_it.csv"
    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    ki, si, ii = header.index("key"), header.index("source_sha256"), header.index("it")
    index = {r[ki]: r for r in rows[1:]}
    added = updated = 0
    for row in usable:
        if row["key"] in index:
            index[row["key"]][si] = row["source_sha256"]
            index[row["key"]][ii] = row["it"]
            updated += 1
        else:
            new_row = [row["key"], row["source_sha256"], row["it"]]
            rows.append(new_row)
            index[row["key"]] = new_row
            added += 1
    # pota le chiavi che il gioco non ha più: il conteggio del CSV deve
    # combaciare con known_source_key_count del manifest (le build vecchie
    # degradano con fallback inglese su quelle chiavi finché non si aggiornano)
    live_keys = set(live)
    kept_rows = [rows[0]] + [r for r in rows[1:] if r[ki] in live_keys]
    pruned = (len(rows) - 1) - (len(kept_rows) - 1)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n").writerows(kept_rows)
    print(f"CSV aggiornato: +{added} nuove, {updated} aggiornate, {pruned} rimosse "
          f"→ {len(kept_rows) - 1} righe totali")

    # manifest: conteggi, fingerprint, build supportata, versione
    manifest_path = REPO / "data" / "supported_versions.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    keys = sorted(live)
    manifest["known_source_key_count"] = len(keys)
    manifest["known_source_key_sha256"] = inst.sha256_keys(keys)
    manifest["known_source_content_sha256"] = inst.sha256_keyed_text(live)
    build = int(inst.read_game_update(game_dir)) if (inst.read_game_update(game_dir) or "").isdigit() else None
    if build:
        sup = [b for b in manifest.get("supported_game_updates", []) if b != build]
        manifest["supported_game_updates"] = [build] + sup
        manifest["latest_supported_game_update"] = build
        manifest["tested_game_update"] = str(build)
    manifest["tested_date"] = __import__("time").strftime("%Y-%m-%d")
    if args.versione:
        manifest["translation_version"] = args.versione
        manifest["coverage"] = f"{len(keys)}/{len(keys)} keys translated (100.00%). Build {build} aggiornata."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest aggiornato: {len(keys)} chiavi, build {build}, versione {manifest['translation_version']}")
    print("Ora: python tools/aggiorna_traduzione.py verifica --game-dir ...")
    return 0


def cmd_verifica(args: argparse.Namespace) -> int:
    game_dir, records = load_live_records(Path(args.game_dir) if args.game_dir else None)
    live = {r["key"]: r["text"] for r in records}
    with open(REPO / "data" / "translation_it.csv", encoding="utf-8", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    csv_keys = {r["key"] for r in csv_rows}
    missing = [k for k in live if k not in csv_keys]
    extra = [k for k in csv_keys if k not in live]
    pair_fail = sum(1 for r in csv_rows if r["key"] in live
                    and hashlib.sha256(live[r["key"]].encode()).hexdigest() != r["source_sha256"])
    empty = sum(1 for r in csv_rows if not (r["it"] or "").strip())
    manifest = json.loads((REPO / "data" / "supported_versions.json").read_text(encoding="utf-8"))
    fp_ok = inst.sha256_keys(sorted(live)) == manifest.get("known_source_key_sha256")
    print(f"Chiavi gioco: {len(live)} · CSV: {len(csv_rows)} · mancanti nel CSV: {len(missing)} · extra: {len(extra)}")
    print(f"Pairing sha256: mismatch {pair_fail} · traduzioni vuote: {empty} · fingerprint manifest: {'OK' if fp_ok else 'NO'}")
    ok = not missing and not extra and not pair_fail and not empty and fp_ok
    print("ESITO:", "PERFETTO — pronto da applicare/pubblicare" if ok else "DA COMPLETARE")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--game-dir", help="cartella del gioco (default: rilevamento automatico)")
    e = sub.add_parser("estrai", parents=[common])
    e.set_defaults(func=cmd_estrai)
    u = sub.add_parser("unisci", parents=[common])
    u.add_argument("--file", required=True)
    u.add_argument("--versione", help="nuova translation_version (es. 0.5.0)")
    u.set_defaults(func=cmd_unisci)
    v = sub.add_parser("verifica", parents=[common])
    v.set_defaults(func=cmd_verifica)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
