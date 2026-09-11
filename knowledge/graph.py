"""Runtime side of the lore graph: expand a retrieval with a query entity's neighbours.

Those neighbours are the facts a vector search misses but a knowledgeable character would connect —
the faction to its base to its aircraft. Reading only; the graph is built offline by build_graph.py.
Gated by the BRAIN_GRAPHRAG flag, off by default, and a missing graph file degrades to a no-op, so an
optional layer can never break retrieval.
"""
from __future__ import annotations

import functools
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.path.join(HERE, "graph.json")


def enabled() -> bool:
    """Flag for the graph-augmented retrieval (default OFF, opt-in). Build/runtime are inert until ON."""
    return os.getenv("BRAIN_GRAPHRAG", "0").strip().lower() in ("1", "on", "true", "yes")


@functools.lru_cache(maxsize=1)
def _graph() -> dict:
    try:
        with open(GRAPH, encoding="utf-8") as f:
            graph = json.load(f)
    except Exception:  # noqa: BLE001 — no graph file -> empty (graceful: retrieval just won't expand)
        return {"nodes": {}, "adj": {}}
    # A readable file of the wrong shape (null, a list, a dict without the two maps) degrades the same
    # way: such a file used to pass the load and then raise from every expansion.
    if not (isinstance(graph, dict) and isinstance(graph.get("nodes"), dict)
            and isinstance(graph.get("adj"), dict)):
        return {"nodes": {}, "adj": {}}
    return graph


def reload() -> None:
    """Drop the cached graph — after a rebuild, or between tests."""
    _graph.cache_clear()


def _resolve(name: str, adj: dict) -> str | None:
    if name in adj:
        return name
    return {k.lower(): k for k in adj}.get(str(name or "").lower())


def neighbors(name: str, hops: int = 1, limit: int = 6) -> list:
    """Related entity names within `hops` of `name` (BFS, nearest first), capped. [] if unknown / no graph."""
    adj = _graph().get("adj", {})
    start = _resolve(name, adj)
    if not start:
        return []
    seen, frontier, out = {start}, [start], []
    for _ in range(max(1, int(hops))):
        nxt = []
        for n in frontier:
            for m in adj.get(n, []):
                if m not in seen:
                    seen.add(m)
                    out.append(m)
                    nxt.append(m)
                    if len(out) >= limit:
                        return out
        frontier = nxt
    return out[:limit]


def neighbors_of(names, hops: int = 1, limit: int = 8) -> list:
    """Union of neighbours across SEVERAL source names (nearest-first per source), deduped, excluding the
    sources themselves, capped. Used to expand a vector-retrieved lore set with its graph connections."""
    seen, out = set(names), []
    for nm in names:
        for nb in neighbors(nm, hops=hops, limit=limit):
            if nb in seen:
                continue
            seen.add(nb)
            out.append(nb)
            if len(out) >= limit:
                return out
    return out


def related_facts(names, limit: int = 6) -> list:
    """For matched entity names, short 'name — description' lines of their graph-neighbours (prompt grounding).
    Skips the query names themselves; deduped; bounded. [] if no graph / nothing related."""
    nodes = _graph().get("nodes", {})
    seen, out = set(names), []
    for nm in names:
        for nb in neighbors(nm, hops=1, limit=4):
            if nb in seen:
                continue
            seen.add(nb)
            desc = (nodes.get(nb, {}).get("desc", "") or "")[:120]
            out.append(f"{nb} — {desc}" if desc else nb)
            if len(out) >= limit:
                return out
    return out
