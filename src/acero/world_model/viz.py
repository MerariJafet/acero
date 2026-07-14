"""A self-contained HTML visualization of the World Model.

Not pretty — useful for thinking. Nodes are laid out in columns by epistemic type
(concept → claim → model → experiment → evidence → contradiction/anomaly → question),
coloured by confidence (red→green), sized by degree. Edges are drawn as lines.
Panels list contradictions, anomalies, weak relations, and critical untested
assumptions. No external CDN — opens offline.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from .graph import WorldModel
from .nodes import NodeType
from .queries import ScientificMemory

_COLUMN_ORDER = [
    NodeType.DOMAIN, NodeType.RESEARCH_PROGRAM, NodeType.PHENOMENON, NodeType.CONCEPT,
    NodeType.DATASET, NodeType.OBSERVATION, NodeType.ASSUMPTION, NodeType.LAW,
    NodeType.THEORY, NodeType.MODEL, NodeType.HYPOTHESIS, NodeType.EXPERIMENT,
    NodeType.EVIDENCE, NodeType.NEGATIVE_RESULT, NodeType.CONTRADICTION,
    NodeType.ANOMALY, NodeType.OPEN_PROBLEM, NodeType.QUESTION,
]


def _color(conf: float) -> str:
    r = int(220 * (1 - conf))
    g = int(180 * conf)
    b = 60
    return f"rgb({r},{g},{b})"


def render_html(wm: WorldModel, *, title: str = "ACERO World Model") -> str:
    nodes = wm.nodes()
    edges = wm.edges(active_only=False)
    mem = ScientificMemory(wm)

    col_index = {t: i for i, t in enumerate(_COLUMN_ORDER)}
    columns: dict[int, list] = {}
    for n in nodes:
        idx = col_index.get(n.type, len(_COLUMN_ORDER))
        columns.setdefault(idx, []).append(n)

    degree: dict[str, int] = {}
    for e in edges:
        degree[e.source] = degree.get(e.source, 0) + 1
        degree[e.target] = degree.get(e.target, 0) + 1

    pos: dict[str, tuple[int, int]] = {}
    col_w, row_h, top = 210, 60, 40
    max_rows = max((len(v) for v in columns.values()), default=1)
    width = (max(columns) + 1) * col_w + 120 if columns else 400
    height = top + max_rows * row_h + 40

    for idx, col_nodes in columns.items():
        x = 60 + idx * col_w
        for j, n in enumerate(sorted(col_nodes, key=lambda z: -z.confidence)):
            pos[n.id] = (x, top + j * row_h)

    svg_edges = []
    for e in edges:
        if e.source in pos and e.target in pos:
            x1, y1 = pos[e.source]
            x2, y2 = pos[e.target]
            dash = "" if e.active else 'stroke-dasharray="4"'
            op = 0.25 + 0.5 * min(1.0, e.weight * e.confidence)
            color = "#c0392b" if e.type.value in ("contradicts", "invalidates") else "#7f8c8d"
            svg_edges.append(
                f'<line x1="{x1+10}" y1="{y1+10}" x2="{x2+10}" y2="{y2+10}" '
                f'stroke="{color}" stroke-opacity="{op:.2f}" {dash}><title>{e.type.value}</title></line>')

    svg_nodes = []
    for n in nodes:
        if n.id not in pos:
            continue
        x, y = pos[n.id]
        r = 6 + min(10, degree.get(n.id, 0))
        label = html.escape(n.label[:22])
        tip = html.escape(f"{n.type.value} · conf={n.confidence:.2f} · {n.label}")
        svg_nodes.append(
            f'<g transform="translate({x},{y})"><circle r="{r}" fill="{_color(n.confidence)}" '
            f'stroke="#333"><title>{tip}</title></circle>'
            f'<text x="{r+3}" y="4" font-size="10" fill="#222">{label}</text></g>')

    def _table(rows: list[str], header: str) -> str:
        items = "".join(f"<li>{html.escape(r)}</li>" for r in rows) or "<li><i>none</i></li>"
        return f"<div class='panel'><h3>{header}</h3><ul>{items}</ul></div>"

    contradictions = [c.label for c in mem.open_contradictions()]
    anomalies = [f"{a.label} (open)" for a in mem.open_anomalies()]
    weak = [f"{w['type']} {w['source'][:8]}→{w['target'][:8]} (strength {w['strength']})"
            for w in mem.weak_relations()]
    critical = [f"{c['assumption']} — {c['n_dependents']} dependents"
                for c in mem.critical_assumptions()]
    single = [n.label for n in mem.single_source_claims()]

    stats = wm.stats()
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:16px;color:#222}}
h1{{font-size:18px}} .meta{{color:#666;font-size:13px}}
.panels{{display:flex;flex-wrap:wrap;gap:16px;margin-top:16px}}
.panel{{border:1px solid #ddd;border-radius:8px;padding:8px 12px;min-width:260px;max-width:420px}}
.panel h3{{margin:4px 0;font-size:14px}} .panel li{{font-size:12px;margin:2px 0}}
svg{{border:1px solid #eee;background:#fafafa}}
.legend span{{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:4px;vertical-align:middle}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="meta">nodes: {stats['n_nodes']} · edges: {stats['n_edges']} (active {stats['active_edges']}) ·
<span class="legend"><span style="background:{_color(0.1)}"></span>low</span>
<span class="legend"><span style="background:{_color(0.9)}"></span>high confidence</span> ·
red edges = contradicts/invalidates · dashed = weakened (inactive)</div>
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
{''.join(svg_edges)}
{''.join(svg_nodes)}
</svg>
<div class="panels">
{_table(contradictions, 'Open contradictions')}
{_table(anomalies, 'Open anomalies')}
{_table(critical, 'Critical untested assumptions')}
{_table(single, 'Single-source claims')}
{_table(weak, 'Weak relations')}
</div>
<script>/* data embedded for inspection */window.ACERO_WM={json.dumps(stats)};</script>
</body></html>"""


def write_html(wm: WorldModel, path: str | Path, *, title: str = "ACERO World Model") -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_html(wm, title=title), encoding="utf-8")
    return str(p)
