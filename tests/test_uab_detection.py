"""Regression: il rilevamento bundle deve essere indipendente dal layout.

Caso reale (2026-09-19): su un secondo PC la copia del gioco deponeva i bundle
uab fuori da DefaultPackage\\CacheBundleFiles e il check diceva 'download
incompleto' a torto. Ora basta qualunque .uab sotto le radici uab.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "tools" / "aniimo_it_installer.py"
SPEC = importlib.util.spec_from_file_location("aniimo_it_installer_uab", INSTALLER_PATH)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = installer
SPEC.loader.exec_module(installer)


class UabDetectionTests(unittest.TestCase):
    def test_bundle_outside_cachebundlefiles_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            odd = game / "Aniimo_Data" / "cvs" / "res" / "uab" / "win" / "CustomPackage" / "v1"
            odd.mkdir(parents=True)
            (odd / "bundle_abc.uab").write_bytes(b"x")
            self.assertTrue(installer._overlay_has_any_bundle(game))
            counts = installer.uab_root_counts(game)
            self.assertEqual(counts[str(Path(r"Aniimo_Data\cvs\res\uab"))], 1)

    def test_worldx_streamingassets_layout_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            odd = game / "worldx_Data" / "StreamingAssets" / "cvs" / "res" / "uab" / "altro"
            odd.mkdir(parents=True)
            (odd / "x.uab").write_bytes(b"x")
            self.assertTrue(installer._overlay_has_any_bundle(game))

    def test_no_bundles_anywhere_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            empty = game / "Aniimo_Data" / "cvs" / "res" / "uab" / "win" / "DefaultPackage"
            empty.mkdir(parents=True)  # cartella presente ma vuota
            self.assertFalse(installer._overlay_has_any_bundle(game))
            counts = installer.uab_root_counts(game)
            self.assertEqual(counts[str(Path(r"Aniimo_Data\cvs\res\uab"))], 0)
            self.assertEqual(counts[str(Path(r"Aniimo_Data\StreamingAssets\cvs\res\uab"))], -1)

    def test_doctor_report_runs_readonly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp)
            report = installer.doctor_report(game)
            self.assertIn("Percorso", report)
            self.assertIn("uab", report)


if __name__ == "__main__":
    unittest.main()
