"""Check that the committed knowledge graph is exactly what the corpus builds.

`knowledge/build_graph.py` is deterministic and offline, and the README promises that a change in
`knowledge/graph.json` means the corpus changed. This gate rebuilds the graph in memory from
`knowledge/world.json`, without character records (they are not part of this repository, and the
build falls back the same way), and compares it with the committed file.

    uv run python -m verification.graph_current
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from knowledge.build_graph import GRAPH, WORLD, build_graph  # noqa: E402


def _edges(graph: dict) -> set[tuple[str, str]]:
    return {tuple(sorted((a, b))) for a, nbrs in graph["adj"].items() for b in nbrs}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    built = build_graph(json.loads(Path(WORLD).read_text(encoding="utf-8")), {})
    committed = json.loads(Path(GRAPH).read_text(encoding="utf-8"))
    if built == committed:
        print(f"graph current: {len(built['nodes'])} nodes, {len(_edges(built))} edges")
        return 0
    problems = []
    for label, a, b in (("nodes only in the rebuild", built["nodes"], committed["nodes"]),
                        ("nodes only in graph.json", committed["nodes"], built["nodes"])):
        extra = sorted(set(a) - set(b))
        if extra:
            problems.append(f"{label}: {len(extra)} ({', '.join(extra[:5])})")
    changed = sorted(n for n in set(built["nodes"]) & set(committed["nodes"])
                     if built["nodes"][n] != committed["nodes"][n])
    if changed:
        problems.append(f"nodes with different data: {len(changed)} ({', '.join(changed[:5])})")
    for label, a, b in (("edges only in the rebuild", _edges(built), _edges(committed)),
                        ("edges only in graph.json", _edges(committed), _edges(built))):
        extra = sorted(a - b)
        if extra:
            problems.append(f"{label}: {len(extra)} ({', '.join(' - '.join(e) for e in extra[:3])})")
    if not problems:
        problems.append("the version field or the key layout differs")
    print("!! knowledge/graph.json is not what knowledge/world.json builds: " + "; ".join(problems)
          + ". Rebuild with `python knowledge/build_graph.py` if the corpus changed on purpose.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
