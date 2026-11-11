"""The interactive event-impact graph (proposal section 8).

    PYTHONPATH=src python scripts/build_graph_explorer.py
    open reports/graph_explorer.html

The proposal's prototype deliverable is "an interactive event-impact graph as
its final output". Static SVG and PNG rendering already exists
(`src/eval/figures.py`), and that is what the report prints; this is the thing
the report cannot be: a reader following a chain from cause to effect, opening
any link, and seeing the evidence that link rests on.

Three constraints shaped it.

**It is one file and loads nothing.** No CDN, no fonts, no network. A grader
opens it from disk, possibly offline, and it must work. Every graph is embedded
as JSON at build time.

**It is written into the repository, not published anywhere.** The spans it
shows are corpus excerpts, and the corpus is licensed research-use, no
redistribution. `data/processed/articles.jsonl` is gitignored for that reason.
The gold graphs' spans are already tracked, so embedding them changes nothing
about what the repository contains - but putting them on a public URL would,
so this file is opened locally and never served.

**It shows provenance, not conclusions.** The distinction the whole study turns
on is `source_asserted` against `model_inferred`, so that is what the page is
built to make visible: solid against dashed, and one click to the span, the
passage id, the publication date and the as-of cutoff it had to clear. A reader
should be able to see where a fluent chain stops being grounded, which is the
problem statement's own wording.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from schema import Graph

REPO = Path(__file__).resolve().parent.parent
GOLD_DIRS = (REPO / "data/eval/gold/dev", REPO / "data/eval/gold/test")
OUTPUT = REPO / "reports/graph_explorer.html"
DEMO = REPO / "tests/fixtures/graph_brent_hormuz.json"


def _load(directories) -> list[dict]:
    graphs = []
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            if path.name == "review_receipt.json":
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["_set"] = directory.name
            graphs.append(payload)
    if not graphs:
        raise SystemExit(f"no graphs found under {', '.join(str(d) for d in directories)}")
    return graphs


def _depths(graph: dict) -> dict[str, int]:
    """Column per variable: the anchor is 0, everything else is its edge's hop.

    A variable reached by more than one edge takes the shallowest, so a chain
    reads left to right without an edge ever pointing backwards.
    """
    anchor = graph["anchor"]["var"]
    depth = {anchor: 0}
    for edge in sorted(graph["edges"], key=lambda e: e["hop"]):
        current = depth.get(edge["dst_var"])
        if current is None or edge["hop"] < current:
            depth[edge["dst_var"]] = edge["hop"]
    for node in graph["nodes"]:
        depth.setdefault(node["var"], max(depth.values(), default=0) + 1)
    return depth


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Event-impact graph explorer</title>
<style>
:root {
  color-scheme: light dark;
  --bg: #fbfbf9; --panel: #ffffff; --ink: #16181d; --muted: #5b6270;
  --line: #d9dce3; --asserted: #176b5d; --inferred: #9a6b16;
  --anchor: #1f3d7a; --chip: #eef1f6; --shadow: 0 1px 2px rgba(16,18,24,.07);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14161a; --panel: #1c1f25; --ink: #e9ecf1; --muted: #9aa3b2;
    --line: #333842; --asserted: #4fbfa8; --inferred: #d9a441;
    --anchor: #7da2e8; --chip: #262b33; --shadow: none;
  }
}
:root[data-theme="dark"] {
  --bg: #14161a; --panel: #1c1f25; --ink: #e9ecf1; --muted: #9aa3b2;
  --line: #333842; --asserted: #4fbfa8; --inferred: #d9a441;
  --anchor: #7da2e8; --chip: #262b33; --shadow: none;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
header { padding: 20px 16px 0; max-width: 1180px; margin: 0 auto; }
h1 { font-size: 1.3rem; margin: 0 0 4px; letter-spacing: -.01em; }
.sub { color: var(--muted); font-size: .88rem; margin: 0 0 14px; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 16px 48px; }
.controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 14px; }
select, button {
  font: inherit; color: var(--ink); background: var(--panel);
  border: 1px solid var(--line); border-radius: 7px; padding: 6px 10px; cursor: pointer;
}
.legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: .82rem; color: var(--muted);
  margin: 0 0 14px; align-items: center; }
.key { display: inline-flex; align-items: center; gap: 6px; }
.key i { width: 26px; height: 0; border-top-width: 2px; display: inline-block; }
.solid { border-top-style: solid; border-color: var(--asserted); }
.dash { border-top-style: dashed; border-color: var(--inferred); }
.board { background: var(--panel); border: 1px solid var(--line); border-radius: 11px;
  box-shadow: var(--shadow); padding: 8px; overflow-x: auto; }
svg { display: block; min-width: 620px; }
.node rect { fill: var(--chip); stroke: var(--line); }
.node.anchor rect { stroke: var(--anchor); stroke-width: 2; }
.node text { fill: var(--ink); font-size: 12px; }
.node .dir { fill: var(--muted); font-size: 11px; }
.edge { cursor: pointer; }
.edge path { fill: none; stroke-width: 1.8; }
.edge.asserted path { stroke: var(--asserted); }
.edge.inferred path { stroke: var(--inferred); stroke-dasharray: 6 4; }
.edge.on path { stroke-width: 3.4; }
.edge text { font-size: 10.5px; fill: var(--muted); }
.detail { margin-top: 14px; background: var(--panel); border: 1px solid var(--line);
  border-radius: 11px; padding: 16px; box-shadow: var(--shadow); }
.detail h2 { font-size: .98rem; margin: 0 0 10px; }
blockquote { margin: 0 0 12px; padding: 10px 14px; border-left: 3px solid var(--asserted);
  background: var(--chip); border-radius: 0 7px 7px 0; font-size: .93rem; }
blockquote.none { border-left-color: var(--inferred); color: var(--muted); font-style: italic; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 5px 14px; margin: 0; font-size: .86rem; }
dt { color: var(--muted); }
dd { margin: 0; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .85em; }
.hint { color: var(--muted); font-size: .86rem; }
.note { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: .84rem; }
footer { max-width: 1180px; margin: 0 auto; padding: 0 16px 40px; color: var(--muted);
  font-size: .8rem; line-height: 1.6; }
@media (max-width: 640px) { .wrap, header, footer { padding-left: 12px; padding-right: 12px; } }
</style>
</head>
<body>
<header>
  <h1>Event-impact graph explorer</h1>
  <p class="sub">Every link is labelled by where it came from. Click one to read the
  evidence it rests on &mdash; or to see that it has none.</p>
</header>
<div class="wrap">
  <div class="controls">
    <select id="pick"></select>
    <button id="theme" type="button">Toggle theme</button>
  </div>
  <div class="legend">
    <span class="key"><i class="solid"></i> source-asserted &mdash; a passage states it</span>
    <span class="key"><i class="dash"></i> model-inferred &mdash; no verified source found</span>
    <span class="key">columns are hop distance from the anchor</span>
  </div>
  <div class="board"><svg id="svg" role="img" aria-label="Event-impact graph"></svg></div>
  <div class="detail" id="detail"><p class="hint">Select a link in the graph above.</p></div>
</div>
<footer id="foot"></footer>
<script>
const GRAPHS = __DATA__;
const svg = document.getElementById('svg');
const detail = document.getElementById('detail');
const pick = document.getElementById('pick');
const NS = 'http://www.w3.org/2000/svg';

GRAPHS.forEach((g, i) => {
  const o = document.createElement('option');
  o.value = i;
  o.textContent = g.query_id + '  \\u00b7  ' + g._set + '  \\u00b7  cutoff ' + g.as_of;
  pick.appendChild(o);
});

const el = (name, attrs, text) => {
  const n = document.createElementNS(NS, name);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text !== undefined) n.textContent = text;
  return n;
};
const esc = (s) => String(s === null || s === undefined ? '' : s);

function layout(g) {
  const COL = 210, ROWH = 62, BOXW = 164, BOXH = 40, PADX = 20, PADY = 26;
  const byDepth = {};
  for (const v in g._depth) (byDepth[g._depth[v]] ||= []).push(v);
  const pos = {};
  let rows = 0;
  Object.keys(byDepth).map(Number).sort((a, b) => a - b).forEach((d) => {
    byDepth[d].sort();
    rows = Math.max(rows, byDepth[d].length);
    byDepth[d].forEach((v, i) => {
      pos[v] = { x: PADX + d * COL, y: PADY + i * ROWH, w: BOXW, h: BOXH };
    });
  });
  const depths = Math.max(...Object.keys(byDepth).map(Number)) + 1;
  return { pos, width: PADX * 2 + (depths - 1) * COL + BOXW, height: PADY * 2 + rows * ROWH };
}

function draw(g) {
  svg.textContent = '';
  const { pos, width, height } = layout(g);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('width', width);
  svg.setAttribute('height', height);

  g.edges.forEach((e) => {
    const a = pos[e.src_var], b = pos[e.dst_var];
    if (!a || !b) return;
    const asserted = e.provenance === 'source_asserted';
    const grp = el('g', {
      class: 'edge ' + (asserted ? 'asserted' : 'inferred'),
      tabindex: '0', role: 'button',
      'aria-label': e.src_var + ' to ' + e.dst_var + ', ' + e.provenance
    });
    const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2;
    const mid = (x1 + x2) / 2;
    grp.appendChild(el('path', { d: `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}` }));
    grp.appendChild(el('text', {
      x: (x1 + x2) / 2, y: (y1 + y2) / 2 - 6, 'text-anchor': 'middle'
    }, e.strength + ' \\u00b7 hop ' + e.hop));
    const show = () => {
      svg.querySelectorAll('.edge.on').forEach((n) => n.classList.remove('on'));
      grp.classList.add('on');
      describe(g, e);
    };
    grp.addEventListener('click', show);
    grp.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); show(); }
    });
    svg.appendChild(grp);
  });

  (g.nodes || []).forEach((n) => {
    const p = pos[n.var];
    if (!p) return;
    const grp = el('g', { class: 'node' + (n.is_anchor ? ' anchor' : '') });
    grp.appendChild(el('rect', { x: p.x, y: p.y, width: p.w, height: p.h, rx: 7 }));
    grp.appendChild(el('text', { x: p.x + 10, y: p.y + 17 }, n.var.replace(/_/g, ' ')));
    const arrow = n.direction === 'up' ? '\\u2191' : n.direction === 'down' ? '\\u2193' : '\\u2192';
    grp.appendChild(el('text', { x: p.x + 10, y: p.y + 31, class: 'dir' },
      arrow + ' ' + n.direction + (n.confirmed_by_series ? ' \\u00b7 series-confirmed' : '')));
    svg.appendChild(grp);
  });
}

function describe(g, e) {
  const asserted = e.provenance === 'source_asserted';
  const quote = asserted
    ? '<blockquote>' + esc(e.evidence_span) + '</blockquote>'
    : '<blockquote class="none">No supporting passage was found and verified under the '
      + 'permitted search. The link is the model\\u2019s reasoning, which is unsourced &mdash; '
      + 'not necessarily wrong.</blockquote>';
  const rows = [
    ['Claim', esc(e.src_var) + ' \\u2192 ' + esc(e.dst_var) + ' (' + esc(e.direction) + ')'],
    ['Provenance', esc(e.provenance)],
    ['Strength', esc(e.strength)],
    ['Hop', esc(e.hop)]
  ];
  if (asserted) {
    rows.push(['Passage', '<code>' + esc(e.evidence_passage_id) + '</code>']);
    rows.push(['Published', esc((e.evidence_published_at || '').slice(0, 10))]);
  }
  rows.push(['Query cutoff', esc(g.as_of)]);
  detail.innerHTML = '<h2>' + esc(e.edge_id) + '</h2>' + quote
    + '<dl>' + rows.map(([k, v]) => '<dt>' + k + '</dt><dd>' + v + '</dd>').join('') + '</dl>'
    + (e.note ? '<p class="note">Annotator note: ' + esc(e.note) + '</p>' : '');
}

function select(i) {
  const g = GRAPHS[i];
  draw(g);
  detail.innerHTML = '<p class="hint">Select a link in the graph above.</p>';
  const paths = (g.paths || []).map((path) =>
    path.edge_ids.join(' → ') + ' · ' + path.weakest_strength +
    ' · ' + (path.fully_sourced ? 'fully sourced' : 'partly inferred')
  );
  document.getElementById('foot').textContent = [g.notes, ...paths].filter(Boolean).join(' | ');
}
pick.addEventListener('change', () => select(+pick.value));

document.getElementById('theme').addEventListener('click', () => {
  const now = document.documentElement.getAttribute('data-theme');
  const next = now === 'dark' ? 'light' : now === 'light' ? 'dark'
    : (matchMedia('(prefers-color-scheme: dark)').matches ? 'light' : 'dark');
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('theme', next); } catch (_) {}
});
try {
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
} catch (_) {}

select(0);
</script>
</body>
</html>
"""


def build(directories=GOLD_DIRS, output: Path = OUTPUT, *, demo=False, run_artifacts=()) -> Path:
    graphs = _load(directories)
    if demo:
        fixture = Graph.model_validate_json(DEMO.read_text(encoding="utf-8"))
        graphs.append(
            {
                **fixture.model_dump(mode="json"),
                "_set": "synthetic example",
                "notes": "Illustrative fixture with synthetic citations and inferred edges.",
            }
        )
    for artifact in run_artifacts:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        graph = Graph.model_validate(payload["graph"])
        graphs.append({**graph.model_dump(mode="json"), "_set": graph.condition or "generated"})
    for graph in graphs:
        graph["_depth"] = _depths(graph)
    payload = json.dumps(graphs, ensure_ascii=False)
    # The data is embedded, so a span carrying markup could end the block early.
    # Escaping only "</" is not enough: a span containing "<!--" followed by
    # "<script" puts the HTML parser into its double-escaped state, where the
    # next "</script>" no longer closes the block. Escaping every "<" as the
    # JSON unicode form removes the whole class of problem, and JSON.parse
    # restores the character, so nothing the reader sees changes.
    payload = payload.replace("<", "\\u003c")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(PAGE.replace("__DATA__", payload), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, nargs="+", default=list(GOLD_DIRS))
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--run-artifact", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    if args.run_artifact and args.output.resolve() == OUTPUT.resolve():
        parser.error("write generated run excerpts to a separate local --output")
    path = build(args.gold, args.output, demo=True, run_artifacts=args.run_artifact)
    print(f"wrote {path} ({path.stat().st_size // 1024} KB)")
    print("Open it from disk. It loads nothing and must not be served: the spans are")
    print("corpus excerpts, and the corpus is research-use, no redistribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
