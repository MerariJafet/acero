"""A first functional dashboard for the Human Understanding Engine.

Renders a static HTML page from the learner's real state: knowledge map, research
requirements, mastery, active misconceptions, prediction-vs-result, why ACERO decided,
what is needed before approving, gate report, and learning history. Clarity over
aesthetics; the point is to let the human INTERVENE, not to look pretty.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

_STATUS_COLOR = {
    "MASTERED": "#1a7f37", "TRANSFER_CAPABLE": "#2da44e",
    "CONCEPTUALLY_UNDERSTOOD": "#3fb950", "PROCEDURALLY_COMPETENT": "#7ee787",
    "PARTIALLY_UNDERSTOOD": "#d4a72c", "RECOGNIZED": "#bf8700", "EXPOSED": "#9a6700",
    "UNKNOWN": "#57606a", "MISCONCEIVED": "#cf222e", "DECAYED": "#8250df",
}


def _chip(concept: str, status: str) -> str:
    color = _STATUS_COLOR.get(status, "#57606a")
    return (f"<span class='chip' style='background:{color}' "
            f"title='{html.escape(status)}'>{html.escape(concept)}</span>")


def _panel(title: str, body: str) -> str:
    return f"<div class='panel'><h3>{html.escape(title)}</h3>{body}</div>"


def _list(items: list[str]) -> str:
    lis = "".join(f"<li>{html.escape(i)}</li>" for i in items) or "<li><i>none</i></li>"
    return f"<ul>{lis}</ul>"


def render_html(*, learner_name: str, status: dict[str, Any],
                knowledge: list[dict[str, Any]], requirements: list[dict[str, Any]],
                misconceptions: list[dict[str, Any]], predictions: list[dict[str, Any]],
                gate_report: dict[str, Any] | None = None,
                title: str = "ACERO — Human Understanding") -> str:
    # Knowledge map
    chips = "".join(_chip(k.get("concept_id", "?"), k.get("status", "UNKNOWN"))
                    for k in knowledge) or "<i>no concepts assessed yet</i>"

    # Research learning requirements
    req_rows = [f"{'⛔ ' if r.get('blocking') else ''}{r.get('concept')} — "
                f"{r.get('reason_required')}" for r in requirements]

    # Mastery buckets
    mastery = _list(status.get("mastered", []) or [])
    partial = _list(status.get("partial", []) or [])

    # Active misconceptions
    misc_rows = [f"{m.get('concept')}: {m.get('statement')} "
                 f"[{m.get('severity')}]{' (resolved)' if m.get('resolved') else ''}"
                 for m in misconceptions if not m.get("resolved")]

    # Prediction vs result
    pred_rows = [f"predicted: {p.get('predicted_outcome')} → result: "
                 f"{p.get('revealed_result') or 'pending'} "
                 f"[{p.get('comparison') or '—'}]" for p in predictions]

    # Why ACERO decided / What I need before approving (from gate report)
    why, needed, gate_line = [], [], "no gate report"
    if gate_report:
        gate_line = f"[{gate_report.get('stage')}] {gate_report.get('outcome')}"
        for b in gate_report.get("blockers", []):
            why.append(f"{b.get('rule')}: {b.get('detail')}")
            if b.get("remediation"):
                needed.append(b["remediation"])

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:1.5rem;background:#0d1117;color:#c9d1d9}}
 h1{{font-size:1.4rem}} h3{{margin:.2rem 0 .5rem;font-size:1rem;color:#58a6ff}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}}
 .panel{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:.8rem}}
 .chip{{display:inline-block;color:#0d1117;font-weight:600;border-radius:12px;
        padding:.1rem .5rem;margin:.15rem;font-size:.8rem}}
 ul{{margin:.2rem 0;padding-left:1.1rem}} li{{margin:.15rem 0}}
 .legend span{{margin-right:.6rem;font-size:.75rem}}
</style></head><body>
<h1>{html.escape(title)} — {html.escape(learner_name)}</h1>
<p class="legend">
 <span style="color:#1a7f37">■ mastered</span>
 <span style="color:#3fb950">■ understood</span>
 <span style="color:#d4a72c">■ partial</span>
 <span style="color:#cf222e">■ misconceived</span>
 <span style="color:#57606a">■ unknown</span></p>
<div class="grid">
 {_panel("My Knowledge Map", f"<div>{chips}</div>")}
 {_panel("Research Learning Requirements", _list(req_rows))}
 {_panel("Concept Mastery", "<b>mastered</b>" + mastery + "<b>partial</b>" + partial)}
 {_panel("Active Misconceptions", _list(misc_rows))}
 {_panel("Prediction vs Result", _list(pred_rows))}
 {_panel("Why ACERO Decided", _list(why or ["— (no blockers)"]))}
 {_panel("What I Need Before Approving", _list(needed or ["— nothing pending"]))}
 {_panel("Gate Report", f"<p>{html.escape(gate_line)}</p>")}
 {_panel("Learning History", _list([f"{e.get('kind')}: {e.get('concept')}"
                                    for e in (status.get('recent_events') or [])]))}
</div></body></html>"""


def write_html(path: str | Path, **kwargs: Any) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_html(**kwargs), encoding="utf-8")
    return str(p)
