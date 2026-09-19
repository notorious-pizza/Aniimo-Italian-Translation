import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_PATH = REPO_ROOT / "tools" / "aniimo_it_installer.py"
SPEC = importlib.util.spec_from_file_location("aniimo_it_installer", INSTALLER_PATH)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = installer
SPEC.loader.exec_module(installer)


def make_game(game: Path, *, write_bundle: bool) -> None:
    """Minimal game dir matching the installer's own path constants.

    LUA_RELS entries contain backslashes: on POSIX they are single literal
    directory names, so join game_dir with the RAW string (not Path parts).
    The font cache area is built the same way, under FONT_CACHE_RELS[0].
    """
    lua = game / installer.LUA_RELS[0]
    lua.mkdir(parents=True)
    (lua / installer.XDF_NAME).write_bytes(b"archive")
    (lua / installer.XDT_NAME).write_bytes(b"index")
    if write_bundle:
        # Real rebundled build: fresh digest dirs inside FONT_CACHE_RELS[0], plus
        # the flat '<n>_<digest>.uab' alias seen by the glob fallback.
        base = game / installer.FONT_CACHE_RELS[0]  # literal-name dir on POSIX
        newdir = base / "9a" / "9abc11119abc11119abc11119abc1111"
        newdir.mkdir(parents=True)
        (newdir / "cdata.uab").write_bytes(b"unknown-rebundled-font-payload")
        (base.parent / "0_9abc11119abc11119abc11119abc1111.uab").write_bytes(
            b"unknown-rebundled-font-payload")


class RebundledFontBuildTests(unittest.TestCase):
    """Build 3551601 rebundled the font bundles: unknown hashes must warn, not block,
    and any residual technical block must point the user at a program update."""

    def test_rebundled_font_warns_but_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            make_game(game, write_bundle=True)
            tech = installer.technical_compatibility_status(installer.resolve_paths(game))
        self.assertIn("native_font_unverified", tech["warnings"])
        self.assertTrue(tech["supported"])

    def test_missing_font_still_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            make_game(game, write_bundle=False)
            tech = installer.technical_compatibility_status(installer.resolve_paths(game))
        self.assertFalse(tech["supported"])
        self.assertIn("native_font_missing", tech["issues"])

    def test_changed_resources_block_message_suggests_program_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            make_game(game, write_bundle=True)
            paths = installer.resolve_paths(game)
            with patch.object(installer, "USER_WORK_DIR", Path(temp) / "work"):
                with self.assertRaisesRegex(RuntimeError, "Aggiorna questo programma"):
                    # Simulate the residual changed-resources case: the font-bundle
                    # check fails only through its issues channel, not as a warning.
                    def fake_status(p):
                        return {"supported": False, "issues": ["native_font_changed"],
                                "warnings": [], "font_verified": False,
                                "date_italian": False, "countdown_italian": False,
                                "font_accented": False, "font_validation": "static_glyph_coverage",
                                "runtime_validation": "pending"}
                    with patch.object(installer, "technical_compatibility_status", fake_status):
                        installer.build_patch(paths, ["en"], force=False)


if __name__ == "__main__":
    unittest.main()
