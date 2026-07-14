"""Knowledge evolution: what changed after an investigation.

Takes a before/after snapshot of the World Model and reports what we now believe
more, less, the same, plus new contradictions, new anomalies, and what to research
next. This is the artefact that turns "ran an experiment" into "learned something".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .graph import WorldModel
from .nodes import NodeType
from .queries import ScientificMemory


@dataclass
class Snapshot:
    confidences: dict[str, float]
    node_ids: set[str]
    labels: dict[str, str]


def snapshot(wm: WorldModel) -> Snapshot:
    nodes = wm.nodes()
    return Snapshot(
        confidences={n.id: n.confidence for n in nodes},
        node_ids={n.id for n in nodes},
        labels={n.id: n.label for n in nodes})


def evolution_report(wm: WorldModel, before: Snapshot, after: Snapshot,
                     *, threshold: float = 0.02) -> dict[str, Any]:
    believe_more: list[dict[str, Any]] = []
    believe_less: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    for nid, conf_after in after.confidences.items():
        conf_before = before.confidences.get(nid)
        if conf_before is None:
            continue  # brand-new node; handled below
        delta = round(conf_after - conf_before, 4)
        entry = {"id": nid, "label": after.labels.get(nid, nid),
                 "before": round(conf_before, 4), "after": round(conf_after, 4), "delta": delta}
        if delta > threshold:
            believe_more.append(entry)
        elif delta < -threshold:
            believe_less.append(entry)
        else:
            unchanged.append(entry)

    new_ids = after.node_ids - before.node_ids
    new_by_type: dict[str, list[str]] = {}
    for nid in new_ids:
        n = wm.get_node(nid)
        if n:
            new_by_type.setdefault(n.type.value, []).append(n.label)

    mem = ScientificMemory(wm)
    next_research = ([q.label for q in wm.nodes(NodeType.QUESTION)][-5:]
                     + [f"Resolve anomaly: {a.label}" for a in mem.open_anomalies()][:3])

    believe_more.sort(key=lambda e: e["delta"], reverse=True)
    believe_less.sort(key=lambda e: e["delta"])
    return {
        "believe_more": believe_more,
        "believe_less": believe_less,
        "unchanged_count": len(unchanged),
        "new_nodes": new_by_type,
        "new_contradictions": new_by_type.get(NodeType.CONTRADICTION.value, []),
        "new_anomalies": new_by_type.get(NodeType.ANOMALY.value, []),
        "next_research": next_research,
        "open_contradictions": len(mem.open_contradictions()),
        "open_anomalies": len(mem.open_anomalies()),
        "critical_untested_assumptions": mem.critical_assumptions()[:5],
    }
