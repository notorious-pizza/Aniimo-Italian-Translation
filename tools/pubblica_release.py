#!/usr/bin/env python3
"""Pubblica una release GitHub con entrambi gli EXE ricompilati.

Procedura codificata (quella collaudata a mano): build PyInstaller dei due spec,
smoke test della GUI, release via API REST (gh release create sulle fork chiede
scope workflow), upload asset con curl, attesa propagazione asset (~4 min).

Uso:
  python tools/pubblica_release.py --titolo "vX.Y.Z — …" [--note-file note.md] [--skip-test]
La versione del tag è letta dal manifest (data/supported_versions.json).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(str(c) for c in cmd[:6]), "…" if len(cmd) > 6 else "")
    return subprocess.run(cmd, cwd=str(REPO), check=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--titolo", required=True)
    ap.add_argument("--note-file", help="file markdown con le note")
    ap.add_argument("--skip-test", action="store_true")
    args = ap.parse_args()

    manifest = json.loads((REPO / "data" / "supported_versions.json").read_text(encoding="utf-8"))
    version = str(manifest.get("translation_version") or "").strip()
    if not version:
        print("translation_version assente nel manifest.")
        return 1
    tag = f"v{version}"
    print(f"Release: {tag} · titolo: {args.titolo}")

    if not args.skip_test:
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                           cwd=str(REPO))
        if r.returncode != 0:
            print("Suite test non verde: release annullata.")
            return 1

    for spec in ("Aniimo-Italian-Translation.spec", "Aniimo-Centro-Controllo.spec"):
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", spec])
    gui = REPO / "dist" / "Aniimo-Centro-Controllo.exe"
    tui = REPO / "dist" / "Aniimo-Italian-Translation.exe"
    smoke = subprocess.run([str(gui), "--smoke"])
    if smoke.returncode != 0:
        print("Smoke test GUI fallito: release annullata.")
        return 1

    tok = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    repo_slug = str(manifest.get("github_repo") or "notorious-pizza/Aniimo-Italian-Translation")
    body = Path(args.note_file).read_text(encoding="utf-8") if args.note_file else args.titolo
    create = subprocess.run(
        ["gh", "api", f"repos/{repo_slug}/releases",
         "-f", f"tag_name={tag}", "-f", "target_commitish=main",
         "-f", f"name={args.titolo}", "-f", f"body={body}", "--jq", ".id"],
        capture_output=True, text=True)
    if create.returncode != 0:
        print("Creazione release fallita:", create.stderr)
        return 1
    rid = create.stdout.strip()
    print(f"Release creata: id {rid} — attesa propagazione…")
    time.sleep(240)
    for exe in (gui, tui):
        up = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "-H", f"Authorization: Bearer {tok}",
             "-H", "Content-Type: application/octet-stream",
             "--data-binary", f"@{exe}",
             f"https://uploads.github.com/repos/{repo_slug}/releases/{rid}/assets?name={exe.name}"],
            capture_output=True, text=True)
        ok = '"state":"uploaded"' in (up.stdout or "")
        print(f"  {exe.name}: {'OK' if ok else 'ERRORE ' + (up.stdout or up.stderr)[:200]}")
        if not ok:
            return 1
    print(f"Pubblicata: https://github.com/{repo_slug}/releases/tag/{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
