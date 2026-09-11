"""Data manifest: designer data changes only on purpose, in a commit that says so.

The atom registry, the state registry, the quests, the milestone and dialect side-cars and the
knowledge corpus are data a designer wrote and cited. The suite loads them but asserted nothing about
what they say, so a guard, an enumeration, a quest's stage label or an allowlist entry could change as
a side effect of another task while every gate stayed green: seeded bugs A15, A17, A18 and A19 of the
first blind catalogue. This gate records a digest of every designer data file, that is every `*.json`
under arbiter/, quests/ and knowledge/, in verification/data_manifest.json, and fails, naming the
files, when one differs, is added or is removed. The digest is sha256 over LF-normalised bytes, so a
Windows and a Linux checkout hash the same.

A deliberate data change records the new state with `--update` in the same commit, where a reviewer
sees the manifest change next to the data. Like the test ratchet, it is never run to turn a red gate
green.

    uv run python -m verification.data_manifest             # check
    uv run python -m verification.data_manifest --update    # record the current state
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "verification" / "data_manifest.json"
DATA_DIRS = ("arbiter", "quests", "knowledge")      # every *.json below these is designer data
_UPDATE = "uv run python -m verification.data_manifest --update"


def digest(data: bytes) -> str:
    """sha256 over LF-normalised bytes, so Windows and Linux checkouts hash the same."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def designer_files(root: Path = ROOT) -> dict[str, str]:
    """Every *.json under the data directories: {path relative to root, forward slashes: digest}."""
    found = {path.relative_to(root).as_posix(): digest(path.read_bytes())
             for top in DATA_DIRS for path in (root / top).rglob("*.json") if path.is_file()}
    return dict(sorted(found.items()))


def compare(recorded: dict[str, str], current: dict[str, str]) -> dict[str, list[str]]:
    """The paths whose digest changed, the paths nobody recorded, and the recorded paths now gone."""
    return {"changed": sorted(p for p in recorded.keys() & current.keys() if recorded[p] != current[p]),
            "added": sorted(current.keys() - recorded.keys()),
            "removed": sorted(recorded.keys() - current.keys())}


def main(argv: list[str] | None = None, root: Path = ROOT, manifest: Path = MANIFEST) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Designer data changes only on purpose")
    ap.add_argument("--update", action="store_true",
                    help="record the current digests, in the same commit as a deliberate data change")
    args = ap.parse_args(argv)

    current = designer_files(root)
    shown = manifest.relative_to(root).as_posix() if manifest.is_relative_to(root) else str(manifest)
    if args.update:
        if not current:
            print(f"!! no designer data under {', '.join(DATA_DIRS)}: nothing to record")
            return 1
        manifest.write_text(json.dumps({"digest": "sha256 of the LF-normalised bytes", "files": current},
                                       ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
        print(f"manifest updated: {len(current)} designer data files")
        return 0

    try:
        recorded = json.loads(manifest.read_text(encoding="utf-8")).get("files")
    except (OSError, ValueError, AttributeError):
        recorded = None
    if not isinstance(recorded, dict) or not recorded:
        # A manifest that is missing or records nothing pins nothing: fail closed, never pass quietly.
        print(f"!! {shown} is missing, unreadable or records no file, so nothing pins the designer "
              f"data. Record the current state with `{_UPDATE}`.")
        return 1
    diff = compare(recorded, current)
    if not any(diff.values()):
        print(f"data manifest: {len(current)} designer data files match {shown}")
        return 0
    found = "; ".join(f"{kind}: {', '.join(paths)}" for kind, paths in diff.items() if paths)
    print(f"!! the designer data differs from {shown}: {found}. A deliberate data change records the "
          f"new state with `{_UPDATE}` in the same commit, where a reviewer sees it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
