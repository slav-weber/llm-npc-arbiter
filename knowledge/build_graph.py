"""Build the lore graph from the structured corpus.

Nodes are entities — items, creatures, lore articles, locations, quests. Edges are co-references
inside descriptions, undirected: an entity whose description names another entity is linked to it.
Deterministic and offline; no model is involved, because the corpus is already structured.

Inflection is handled by prefix matching (`\\bName\\w*`), so a mention in an oblique case still
resolves to the entity, and aliases recorded in the corpus resolve to their canonical name. Names
shorter than MIN_TERM are ignored: they match too much to mean anything.

If a file of character records is present next to the corpus, named characters become nodes too and
their stated kin become explicit edges. That file is not part of this repository, so the build falls
back to a plain lore graph.

Output is `graph.json`, which `graph.py` walks at runtime. Rebuild it when the corpus changes:

    python knowledge/build_graph.py
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD = os.path.join(HERE, "world.json")
GRAPH = os.path.join(HERE, "graph.json")
_CATS = ("items", "critters", "lore", "locations", "quests")
MIN_TERM = 4  # ignore very short names: they match substrings everywhere and add only noise


def _entity(e):
    """(name, desc, region, aliases) from a corpus entry.

    An entry is a dict, or a bare string — the locations category holds both shapes.
    """
    if isinstance(e, str):
        return e.strip(), "", "", []
    if isinstance(e, dict):
        return (str(e.get("name") or "").strip(), str(e.get("desc") or e.get("text") or ""),
                str(e.get("region") or ""), [str(a) for a in (e.get("aliases") or []) if str(a).strip()])
    return "", "", "", []


def _parse_kin(kin: str) -> list:
    """A kin field, "Name:relation;Name2:relation2", to [Name, Name2] — the part before the colon."""
    out = []
    for part in (kin or "").split(";"):
        t = part.split(":", 1)[0].strip()
        if t:
            out.append(t)
    return out


def build_graph(corpus: dict, facts: dict | None = None) -> dict:
    """Pure: corpus (plus optional character records) -> {version, nodes, adj}.

    Edges are undirected co-references of names inside descriptions, prefix-matched so an inflected
    mention still resolves, and alias-aware. When `facts` is given, named characters become nodes of
    type "npc": their names join the co-reference pass, so a lore article that mentions a character
    links to them, and their kin targets become explicit edges. A kin target with no node of its own
    (a generic "sister", say) is skipped. Everything lands in the same graph, so the runtime does not
    need to know whether characters were included.
    """
    nodes: dict = {}
    alias2canon: dict = {}
    for cat in _CATS:
        for e in (corpus.get(cat) or []):
            name, desc, region, aliases = _entity(e)
            if not name:
                continue
            nodes.setdefault(name, {"type": cat, "region": region, "desc": desc[:300]})
            alias2canon.setdefault(name.lower(), name)
            for a in aliases:
                alias2canon.setdefault(a.lower(), name)
    # Character records become nodes, and their names go into the alias table so the co-reference
    # pass catches mentions of them in lore descriptions. Kin edges are added after that pass.
    npc_kin = []
    for rec in (facts or {}).values():
        if not (isinstance(rec, dict) and rec.get("named")):
            continue
        nm = str(rec.get("name") or "").strip()
        if not nm:
            continue
        nodes.setdefault(nm, {"type": "npc", "region": "", "desc": str(rec.get("profession") or "")[:300]})
        alias2canon.setdefault(nm.lower(), nm)
        tg = _parse_kin(rec.get("kin", ""))
        if tg:
            npc_kin.append((nm, tg))
    terms = sorted({t for t in alias2canon if len(t) >= MIN_TERM}, key=len, reverse=True)
    adj: dict = {}
    if terms:
        # Prefix match `\bterm\w*`, so a mention in an oblique case still links to the entity.
        rx = re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\w*", re.IGNORECASE)
        for name, info in nodes.items():
            hay = info.get("desc") or ""
            if not hay:
                continue
            for hit in {m.lower() for m in rx.findall(hay)}:
                canon = alias2canon.get(hit)
                if canon and canon != name:
                    adj.setdefault(name, set()).add(canon)
                    adj.setdefault(canon, set()).add(name)  # undirected
    # Explicit kin edges from the character records; a target with no node is skipped.
    for nm, targets in npc_kin:
        for t in targets:
            canon = alias2canon.get(t.lower())
            if canon and canon != nm:
                adj.setdefault(nm, set()).add(canon)
                adj.setdefault(canon, set()).add(nm)
    return {"version": 1, "nodes": nodes, "adj": {k: sorted(v) for k, v in adj.items()}}


def main():
    with open(WORLD, encoding="utf-8") as f:
        corpus = json.load(f)
    facts = {}
    try:  # Character records, when the runtime provides them; absent here -> a plain lore graph.
        with open(os.path.join(HERE, "..", "npc_facts.json"), encoding="utf-8") as f:
            facts = json.load(f)
    except (OSError, ValueError):
        pass
    g = build_graph(corpus, facts)
    with open(GRAPH, "w", encoding="utf-8") as f:
        json.dump(g, f, ensure_ascii=False)
    edges = sum(len(v) for v in g["adj"].values()) // 2
    npc = sum(1 for v in g["nodes"].values() if v.get("type") == "npc")
    print(f"[graph] nodes={len(g['nodes'])} (npc={npc}) linked={len(g['adj'])} edges={edges} -> {GRAPH}")


if __name__ == "__main__":
    main()
