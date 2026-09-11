"""The data-manifest gate names every designer data file that changed, appeared or disappeared.

Run against a small temporary tree, never against the repository's own data: the gate itself checks
that (`python -m verification.data_manifest`).
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verification import data_manifest    # noqa: E402


class DataManifest(unittest.TestCase):
    """Check mode and --update, on a throwaway tree with the same layout as the repository."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.manifest = self.root / "verification" / "data_manifest.json"
        self.manifest.parent.mkdir()
        self._write("arbiter/atom_registry.json", b'{"rescue": {"guard": "gvar(71)==1"}}\n')
        self._write("arbiter/registry/fo2.state.json", b'{"status": ["alive", "dead", "fled"]}\n')
        self._write("quests/q198_klamath_still.json", b'{\n  "val": 4,\n  "phase": "failed"\n}\n')
        self._write("knowledge/world.json", b'{"lore": []}\n')

    def _write(self, rel: str, data: bytes) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _run(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = data_manifest.main(list(argv), root=self.root, manifest=self.manifest)
        return code, out.getvalue()

    def test_a_changed_added_or_removed_file_fails_and_is_named(self):
        """Each kind of difference fails the check and names the file under its own heading."""
        self.assertEqual(self._run("--update")[0], 0)
        code, out = self._run()
        self.assertEqual(code, 0, out)

        self._write("quests/q198_klamath_still.json", b'{\n  "val": 4,\n  "phase": "done"\n}\n')
        self._write("arbiter/registry/mod.state.json", b'{"domains": {}}\n')
        (self.root / "knowledge" / "world.json").unlink()
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertIn("changed: quests/q198_klamath_still.json", out)
        self.assertIn("added: arbiter/registry/mod.state.json", out)
        self.assertIn("removed: knowledge/world.json", out)

    def test_line_endings_are_not_a_change(self):
        """A CRLF checkout of the same data hashes like the LF one it was recorded from."""
        self._run("--update")
        self._write("quests/q198_klamath_still.json", b'{\r\n  "val": 4,\r\n  "phase": "failed"\r\n}\r\n')
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_only_json_under_the_data_directories_is_pinned(self):
        """Code, notes and JSON outside arbiter/, quests/ and knowledge/ are not designer data."""
        self._run("--update")
        self._write("arbiter/atom_gate.py", b"# code\n")
        self._write("quests/README.md", b"notes\n")
        self._write("verification/test_inventory.json", b'{"tests": []}\n')
        code, out = self._run()
        self.assertEqual(code, 0, out)

    def test_a_missing_or_empty_manifest_fails_closed(self):
        """A manifest that is absent, or records no file, pins nothing: the check fails, loudly."""
        code, out = self._run()
        self.assertEqual(code, 1, out)
        self.assertTrue(out.startswith("!!"), out)
        self.manifest.write_text('{"files": {}}\n', encoding="utf-8")
        code, out = self._run()
        self.assertEqual(code, 1, out)


if __name__ == "__main__":
    unittest.main()
