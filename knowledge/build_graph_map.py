"""Render the lore graph as one self-contained, dependency-free HTML page.

Reads the graph built by ``build_graph.py`` (nodes + undirected adjacency) and the structured
corpus it was built from, computes a force-directed layout ONCE at build time, and writes a
single HTML file with an inline SVG. No JavaScript library, no CDN, no network: the page opens
from disk and works offline, which is the same discipline the runtime follows.

The layout is deterministic (fixed seed, fixed iteration count), so rebuilding the same graph
produces the same picture and a diff shows a real change in the corpus, not simulation noise.

    python knowledge/build_graph_map.py            # -> docs/knowledge-graph.html
    python knowledge/build_graph_map.py --min-degree 2 --out docs/graph-core.html
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GRAPH = os.path.join(HERE, "graph.json")
WORLD = os.path.join(HERE, "world.json")
DEFAULT_OUT = os.path.join(ROOT, "docs", "knowledge-graph.html")

# Corpus categories, in the order they are drawn and listed in the legend.
CATEGORIES = ("lore", "locations", "critters", "items", "quests")
COLOURS = {
    "lore": "#c9782f",
    "locations": "#2f7d8c",
    "critters": "#8c2f4a",
    "items": "#4a6b2f",
    "quests": "#5b4a8c",
    "": "#6b6b6b",
}

W, H = 1600, 1100          # SVG user-space canvas
SEED = 20260910


def _categories(world: dict) -> dict[str, str]:
    """Map an entity name to the corpus category it came from (first match wins)."""
    out: dict[str, str] = {}
    for cat in CATEGORIES:
        for entry in world.get(cat, []):
            name = entry if isinstance(entry, str) else (entry.get("name") or "")
            if name and name not in out:
                out[name] = cat
    return out


_LATIN = re.compile(r"^[A-Za-z0-9]")


def _labels(world: dict) -> dict[str, str]:
    """Entity name -> the label to draw.

    The corpus is built from the game files of the player's own installation, so the entity names
    are in that installation's language. Where the corpus itself already records a Latin-script
    alias (52 of the 76 lore entries do), that alias is drawn instead: it is the canonical name of
    the same entity, taken from the data, not a translation invented here.
    """
    out: dict[str, str] = {}
    for cat in CATEGORIES:
        for entry in world.get(cat, []):
            if isinstance(entry, str):
                continue
            name = entry.get("name") or ""
            if not name or name in out:
                continue
            for alias in entry.get("aliases") or ():
                if isinstance(alias, str) and _LATIN.match(alias.strip()):
                    out[name] = alias.strip()
                    break
    return out


def _components(adj: dict[str, list[str]]) -> list[list[str]]:
    """Connected components, largest first — the layout packs them side by side."""
    seen: set[str] = set()
    comps: list[list[str]] = []
    for start in adj:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            node = stack.pop()
            comp.append(node)
            for nb in adj.get(node, ()):
                if nb not in seen and nb in adj:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)
    comps.sort(key=len, reverse=True)
    return comps


def _layout(nodes: list[str], adj: dict[str, list[str]], iterations: int = 600) -> dict[str, tuple[float, float]]:
    """Fruchterman-Reingold force layout with a fixed seed: same graph, same picture.

    A weak pull toward the centre is added to the classic algorithm, otherwise sparsely connected
    entities drift to the frame and the picture reads as a band rather than a map.
    """
    rng = random.Random(SEED)
    n = max(1, len(nodes))
    area = W * H
    k = math.sqrt(area / n)                      # ideal edge length
    # Start on a circle rather than at random: fewer iterations to an untangled layout.
    pos = {v: [W / 2 + math.cos(2 * math.pi * i / n) * W / 3 + rng.uniform(-6, 6),
               H / 2 + math.sin(2 * math.pi * i / n) * H / 3 + rng.uniform(-6, 6)]
           for i, v in enumerate(nodes)}
    index = set(nodes)
    edges = [(u, v) for u in nodes for v in adj.get(u, ()) if v in index and u < v]
    temperature = W / 8.0
    cooling = temperature / (iterations + 1)

    for _ in range(iterations):
        disp = {v: [0.0, 0.0] for v in nodes}
        # Repulsion between every pair. The graph is small enough (hundreds of nodes) that the
        # quadratic pass is cheaper than the bookkeeping of a quadtree, and it stays exact.
        for i, u in enumerate(nodes):
            ux, uy = pos[u]
            for v in nodes[i + 1:]:
                dx, dy = ux - pos[v][0], uy - pos[v][1]
                dist2 = dx * dx + dy * dy
                if dist2 < 0.01:
                    dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
                    dist2 = dx * dx + dy * dy + 0.01
                force = (k * k) / dist2
                disp[u][0] += dx * force
                disp[u][1] += dy * force
                disp[v][0] -= dx * force
                disp[v][1] -= dy * force
        # Attraction along edges.
        for u, v in edges:
            dx, dy = pos[u][0] - pos[v][0], pos[u][1] - pos[v][1]
            dist = math.hypot(dx, dy) or 0.01
            force = (dist * dist) / k / dist
            disp[u][0] -= dx * force
            disp[u][1] -= dy * force
            disp[v][0] += dx * force
            disp[v][1] += dy * force
        # Gravity: a weak pull toward the centre, stronger for poorly connected nodes.
        for v in nodes:
            gx, gy = W / 2 - pos[v][0], H / 2 - pos[v][1]
            pull = 0.022 / (1.0 + math.sqrt(len(adj.get(v, ()))))
            disp[v][0] += gx * pull
            disp[v][1] += gy * pull
        # Move, capped by the current temperature. Nothing is clamped to the canvas here: a hard
        # wall makes nodes pile up along the frame. The result is rescaled to fit once, at the end.
        for v in nodes:
            dx, dy = disp[v]
            dist = math.hypot(dx, dy) or 0.01
            step = min(dist, temperature)
            pos[v][0] += dx / dist * step
            pos[v][1] += dy / dist * step
        temperature -= cooling

    return _fit(pos)


def _fit(pos: dict[str, list[float]], margin: float = 46.0) -> dict[str, tuple[float, float]]:
    """Scale a free layout into the canvas, preserving the aspect ratio."""
    xs = [p[0] for p in pos.values()] or [0.0]
    ys = [p[1] for p in pos.values()] or [0.0]
    span_x = (max(xs) - min(xs)) or 1.0
    span_y = (max(ys) - min(ys)) or 1.0
    scale = min((W - 2 * margin) / span_x, (H - 2 * margin) / span_y)
    off_x = (W - span_x * scale) / 2 - min(xs) * scale
    off_y = (H - span_y * scale) / 2 - min(ys) * scale
    return {v: (round(p[0] * scale + off_x, 1), round(p[1] * scale + off_y, 1))
            for v, p in pos.items()}


def _relax(pos: dict[str, tuple[float, float]], sep_x: float = 78.0, sep_y: float = 26.0,
           rounds: int = 140) -> dict[str, tuple[float, float]]:
    """Push apart nodes whose labels would overlap.

    The force layout optimises edge lengths, not readability: a dense cluster ends up with circles
    and labels on top of each other. Separation is elliptical rather than circular because a label
    is a wide, short box — two entities can sit close vertically and still be legible, but not
    horizontally. The picture is refitted to the canvas afterwards.
    """
    keys = list(pos)
    p = {v: [x, y] for v, (x, y) in pos.items()}
    ratio = sep_x / sep_y
    for _ in range(rounds):
        moved = False
        for i, u in enumerate(keys):
            for v in keys[i + 1:]:
                dx = p[u][0] - p[v][0]
                dy = (p[u][1] - p[v][1]) * ratio          # work in a space where the ellipse is a circle
                dist = math.hypot(dx, dy)
                if dist >= sep_x:
                    continue
                if dist < 0.01:
                    dx, dy, dist = 0.7, 0.4, 0.81
                shift = (sep_x - dist) / 2.0
                ux, uy = dx / dist * shift, dy / dist * shift / ratio
                p[u][0] += ux
                p[u][1] += uy
                p[v][0] -= ux
                p[v][1] -= uy
                moved = True
        if not moved:
            break
    return _fit(p)


def _pack(adj: dict[str, list[str]]) -> dict[str, tuple[float, float]]:
    """Main component fills the canvas; small components sit in a strip along the bottom."""
    comps = _components(adj)
    if not comps:
        return {}
    rest = [c for c in comps[1:] if len(c) > 1]
    if not rest:
        return _relax(_layout(comps[0], adj))

    strip_h = min(H * 0.22, 60 + 26 * len(rest))
    main = _relax(_layout(comps[0], adj))
    squeeze = (H - strip_h - 60) / H
    pos: dict[str, tuple[float, float]] = {
        v: (x, y * squeeze + 20) for v, (x, y) in main.items()
    }

    # Satellites: laid out on their own, scaled to a cell, placed left to right.
    cell_w = W / len(rest)
    base_y = H - strip_h / 2
    for i, comp in enumerate(rest):
        sub = _fit({v: [x, y] for v, (x, y) in _layout(comp, adj, iterations=180).items()},
                   margin=W * 0.30)
        xs = [p[0] for p in sub.values()]
        ys = [p[1] for p in sub.values()]
        span_x = (max(xs) - min(xs)) or 1.0
        span_y = (max(ys) - min(ys)) or 1.0
        box = min(cell_w * 0.62, strip_h * 0.62)
        scale = min(box / span_x, box / span_y)
        cx = cell_w * (i + 0.5)
        for v, (x, y) in sub.items():
            pos[v] = (round(cx + (x - (min(xs) + span_x / 2)) * scale, 1),
                      round(base_y + (y - (min(ys) + span_y / 2)) * scale, 1))
    return pos


def build(min_degree: int = 1, out_path: str = DEFAULT_OUT) -> str:
    with open(GRAPH, encoding="utf-8") as f:
        graph = json.load(f)
    with open(WORLD, encoding="utf-8") as f:
        world = json.load(f)

    adj_all: dict[str, list[str]] = {k: list(v) for k, v in graph.get("adj", {}).items()}
    cats = _categories(world)
    labels = _labels(world)
    nodes_meta = graph.get("nodes", {})

    kept = {v for v, nbs in adj_all.items() if len(nbs) >= min_degree}
    adj = {v: [n for n in adj_all[v] if n in kept] for v in kept}
    adj = {v: nbs for v, nbs in adj.items() if nbs}
    # Dropping the neighbourless leaves a second time can orphan a name that other nodes still
    # list, so re-filter until the adjacency only names nodes that are actually drawn. Otherwise
    # the panel would claim a connection the picture cannot show.
    while True:
        drawn = set(adj)
        pruned = {v: [n for n in nbs if n in drawn] for v, nbs in adj.items()}
        pruned = {v: nbs for v, nbs in pruned.items() if nbs}
        if pruned == adj:
            break
        adj = pruned
    pos = _pack(adj)
    order = sorted(adj, key=lambda v: (-len(adj[v]), v))

    edges = sorted({(u, v) if u < v else (v, u) for u in adj for v in adj[u]})
    svg_edges = "".join(
        f'<line class="e" data-a="{html.escape(u)}" data-b="{html.escape(v)}" '
        f'x1="{pos[u][0]}" y1="{pos[u][1]}" x2="{pos[v][0]}" y2="{pos[v][1]}"/>'
        for u, v in edges if u in pos and v in pos
    )

    svg_nodes = []
    for v in order:
        if v not in pos:
            continue
        deg = len(adj[v])
        r = round(3.4 + math.sqrt(deg) * 2.6, 1)
        cat = cats.get(v, "")
        meta = nodes_meta.get(v) or {}
        desc = (meta.get("desc") or "").strip().replace("\n", " ")
        if len(desc) > 260:
            desc = desc[:257] + "…"
        svg_nodes.append(
            f'<g class="n" data-id="{html.escape(v)}" data-cat="{cat}" data-deg="{deg}" '
            f'data-desc="{html.escape(desc, quote=True)}" '
            f'data-nb="{html.escape("|".join(sorted(adj[v])), quote=True)}" '
            f'data-src="{html.escape(v if v in labels else "", quote=True)}">'
            f'<circle cx="{pos[v][0]}" cy="{pos[v][1]}" r="{r}" fill="{COLOURS.get(cat, COLOURS[""])}"/>'
            f'<text x="{pos[v][0]}" y="{pos[v][1] - r - 3.5}">{html.escape(labels.get(v, v))}</text></g>'
        )

    counts = {c: sum(1 for v in adj if cats.get(v, "") == c) for c in CATEGORIES}
    counts_other = sum(1 for v in adj if cats.get(v, "") not in CATEGORIES)
    legend = "".join(
        f'<button class="lg" data-cat="{c}"><i style="background:{COLOURS[c]}"></i>'
        f'{c} <b>{counts[c]}</b></button>' for c in CATEGORIES if counts[c]
    )
    if counts_other:
        legend += (f'<button class="lg" data-cat=""><i style="background:{COLOURS[""]}"></i>'
                   f'other <b>{counts_other}</b></button>')

    # The viewBox follows the drawing, not the layout canvas, so the picture fills the pane
    # instead of sitting in a letterbox.
    xs = [p[0] for p in pos.values()] or [0.0]
    ys = [p[1] for p in pos.values()] or [0.0]
    pad = 40.0
    vb = (round(min(xs) - pad, 1), round(min(ys) - pad * 0.8, 1),
          round(max(xs) - min(xs) + 2 * pad, 1), round(max(ys) - min(ys) + 1.8 * pad, 1))

    page = _PAGE.format(
        nodes=len(adj), edges=len(edges), corpus=sum(len(world.get(c, [])) for c in CATEGORIES),
        min_degree=min_degree, legend=legend, svg_edges=svg_edges,
        svg_nodes="".join(svg_nodes), viewbox=" ".join(str(x) for x in vb),
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print(f"[graph-map] {len(adj)} nodes, {len(edges)} edges (min degree {min_degree}) -> {out_path}")
    return out_path


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lore knowledge graph</title>
<style>
  :root {{ color-scheme: light dark; --bg:#f5f4f1; --fg:#1d2126; --mut:#6a7178; --line:#d8d6d1; --panel:#fff; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#14181c; --fg:#e7ebee; --mut:#98a1a9; --line:#2a3138; --panel:#1b2126; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
         font:15px/1.5 "Segoe UI",system-ui,sans-serif; }}
  header {{ padding:14px 20px; border-bottom:1px solid var(--line); display:flex;
            flex-wrap:wrap; gap:10px 22px; align-items:baseline; }}
  h1 {{ font-size:18px; margin:0; font-weight:600; }}
  .stat {{ color:var(--mut); font-size:13px; }}
  .tools {{ display:flex; gap:8px; margin-left:auto; align-items:center; flex-wrap:wrap; }}
  input[type=search] {{ padding:5px 9px; border:1px solid var(--line); border-radius:6px;
                        background:var(--panel); color:inherit; min-width:190px; font:inherit; }}
  .lg {{ display:inline-flex; align-items:center; gap:6px; padding:3px 9px; border:1px solid var(--line);
         border-radius:999px; background:var(--panel); color:inherit; cursor:pointer; font:inherit;
         font-size:13px; }}
  .lg.off {{ opacity:.35; }}
  .lg i {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
  .lg b {{ font-weight:600; color:var(--mut); }}
  main {{ position:relative; }}
  svg {{ display:block; width:100%; height:calc(100vh - 62px); background:var(--bg); }}
  .e {{ stroke:var(--line); stroke-width:.9; }}
  .n text {{ font-size:8.5px; fill:var(--mut); text-anchor:middle; pointer-events:none;
             paint-order:stroke; stroke:var(--bg); stroke-width:2.6px; }}
  .n circle {{ cursor:pointer; }}
  .n.dim {{ opacity:.12; }}
  .n.hide, .e.hide {{ display:none; }}
  .n.hot text {{ fill:var(--fg); font-size:11px; font-weight:600; }}
  .e.hot {{ stroke:var(--fg); stroke-width:1.8; }}
  .e.dim {{ opacity:.12; }}
  aside {{ position:absolute; top:14px; right:14px; width:290px; background:var(--panel);
           border:1px solid var(--line); border-radius:10px; padding:12px 14px; display:none; }}
  aside.on {{ display:block; }}
  aside h2 {{ margin:0 0 2px; font-size:15px; }}
  aside .k {{ color:var(--mut); font-size:12px; margin-bottom:8px; }}
  aside p {{ margin:0 0 8px; font-size:13px; }}
  aside ul {{ margin:0; padding-left:16px; font-size:13px; max-height:210px; overflow:auto; }}
  footer {{ padding:10px 20px; border-top:1px solid var(--line); color:var(--mut); font-size:12px; }}
</style>
</head>
<body>
<header>
  <h1>Lore knowledge graph</h1>
  <span class="stat">{nodes} linked entities · {edges} edges · corpus of {corpus} entities ·
    nodes with degree &lt; {min_degree} hidden</span>
  <span class="tools">{legend}<input type="search" id="q" placeholder="find an entity"></span>
</header>
<main>
<svg viewBox="{viewbox}" preserveAspectRatio="xMidYMid meet" id="svg">
<g id="edges">{svg_edges}</g>
<g id="nodes">{svg_nodes}</g>
</svg>
<aside id="card"><h2 id="c-name"></h2><div class="k" id="c-meta"></div>
<p id="c-desc"></p><ul id="c-nb"></ul></aside>
</main>
<footer>Built offline by <code>knowledge/build_graph_map.py</code> from the graph that the runtime
walks. Edges are co-references: an entity whose description names another entity is linked to it.
The layout is deterministic, so the same corpus always draws the same map. The corpus is extracted
from the game files of the player's own installation, so entity names appear in that installation's
language; where the corpus itself records a canonical Latin-script alias, that alias is drawn and the
original name is shown in the panel.</footer>
<script>
'use strict';
const nodes = [...document.querySelectorAll('.n')];
const edges = [...document.querySelectorAll('.e')];
const card = document.getElementById('card');
const off = new Set();
const byId = new Map(nodes.map(n => [n.dataset.id, n]));
const label = id => {{ const n = byId.get(id); return n ? n.querySelector('text').textContent : ''; }};
let pinned = null;

function highlight(id) {{
  if (!id) {{
    nodes.forEach(n => n.classList.remove('dim', 'hot'));
    edges.forEach(e => e.classList.remove('dim', 'hot'));
    card.classList.remove('on');
    return;
  }}
  const node = nodes.find(n => n.dataset.id === id);
  if (!node) return;
  const nb = new Set(node.dataset.nb ? node.dataset.nb.split('|') : []);
  nodes.forEach(n => {{
    const near = n.dataset.id === id || nb.has(n.dataset.id);
    n.classList.toggle('dim', !near);
    n.classList.toggle('hot', near);
  }});
  edges.forEach(e => {{
    const near = e.dataset.a === id || e.dataset.b === id;
    e.classList.toggle('hot', near);
    e.classList.toggle('dim', !near);
  }});
  document.getElementById('c-name').textContent = node.querySelector('text').textContent;
  document.getElementById('c-meta').textContent =
    (node.dataset.cat || 'other') + ' · ' + node.dataset.deg + ' connections' +
    (node.dataset.src ? ' · in the corpus: ' + node.dataset.src : '');
  document.getElementById('c-desc').textContent = node.dataset.desc || '';
  document.getElementById('c-nb').innerHTML =
    [...nb].map(x => '<li>' + (label(x) || x).replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c])) + '</li>').join('');
  card.classList.add('on');
}}

function applyFilter() {{
  const hidden = new Set();
  nodes.forEach(n => {{
    const drop = off.has(n.dataset.cat);
    n.classList.toggle('hide', drop);
    if (drop) hidden.add(n.dataset.id);
  }});
  edges.forEach(e => e.classList.toggle('hide', hidden.has(e.dataset.a) || hidden.has(e.dataset.b)));
}}

document.getElementById('nodes').addEventListener('click', ev => {{
  const g = ev.target.closest('.n');
  if (!g) return;
  pinned = pinned === g.dataset.id ? null : g.dataset.id;
  highlight(pinned);
}});
document.getElementById('nodes').addEventListener('mouseover', ev => {{
  const g = ev.target.closest('.n');
  if (g && !pinned) highlight(g.dataset.id);
}});
document.getElementById('svg').addEventListener('mouseleave', () => {{ if (!pinned) highlight(null); }});
document.querySelectorAll('.lg').forEach(b => b.addEventListener('click', () => {{
  const c = b.dataset.cat;
  if (off.has(c)) {{ off.delete(c); b.classList.remove('off'); }}
  else {{ off.add(c); b.classList.add('off'); }}
  applyFilter();
}}));
document.getElementById('q').addEventListener('input', ev => {{
  const term = ev.target.value.trim().toLowerCase();
  if (!term) {{ pinned = null; highlight(null); return; }}
  const hit = nodes.find(n => (n.dataset.id + ' ' + n.querySelector('text').textContent)
    .toLowerCase().includes(term));
  if (hit) {{ pinned = hit.dataset.id; highlight(pinned); }}
}});
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the lore graph as a self-contained HTML map.")
    ap.add_argument("--min-degree", type=int, default=1,
                    help="hide entities with fewer connections than this (default 1)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output HTML path")
    args = ap.parse_args()
    build(min_degree=args.min_degree, out_path=args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
