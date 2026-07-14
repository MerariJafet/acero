"""Adversarial audit of the World Model (rules + optional Codex).

Asks: does it really learn? are there redundant relations? is information lost? are
there absurd cycles? what still looks like a traditional database? Rule findings are
deterministic; Codex findings are advisory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .edges import EdgeType
from .graph import WorldModel
from .nodes import BELIEF_TYPES


@dataclass
class Finding:
    concern: str
    detail: str
    severity: str
    source: str = "rules"


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"n_findings": len(self.findings),
                "findings": [f.__dict__ for f in self.findings]}


def rules_audit(wm: WorldModel) -> AuditReport:
    f: list[Finding] = []
    nodes = wm.nodes()
    edges = wm.edges(active_only=False)

    # Does it learn? At least one belief must have changed confidence (history > 1).
    learned = 0
    for n in nodes:
        if n.type in BELIEF_TYPES and len(n.belief.get("history", [])) >= 1:
            learned += 1
    if learned == 0:
        f.append(Finding("does_not_learn",
                         "No belief has an update history; the graph is static.", "high"))

    # Redundant relations: duplicate (source, target, type) among ACTIVE edges.
    # Inactive/weakened duplicates are legitimate history, not redundancy.
    seen: set[tuple[str, str, str]] = set()
    dups = 0
    for e in edges:
        if not e.active:
            continue
        key = (e.source, e.target, e.type.value)
        if key in seen:
            dups += 1
        seen.add(key)
    if dups:
        f.append(Finding("redundant_relations",
                         f"{dups} duplicate active edge(s) (same source/target/type).", "medium"))

    # Information loss: belief nodes with no persisted history rows.
    lost = [n.label for n in nodes
            if n.type in BELIEF_TYPES and not wm.node_history(n.id)]
    if lost:
        f.append(Finding("possible_information_loss",
                         f"{len(lost)} belief(s) without persisted history.", "high"))

    # Absurd cycles: A depends_on B and B depends_on A.
    dep = {(e.source, e.target) for e in edges if e.type == EdgeType.DEPENDS_ON}
    cycles = [(a, b) for (a, b) in dep if (b, a) in dep and a < b]
    if cycles:
        f.append(Finding("dependency_cycle",
                         f"{len(cycles)} mutual depends_on cycle(s).", "high"))
    self_loops = [e.id for e in edges if e.source == e.target]
    if self_loops:
        f.append(Finding("self_loops", f"{len(self_loops)} self-loop edge(s).", "medium"))

    # Still a database? Too many generic RELATED_TO edges vs typed epistemic ones.
    if edges:
        generic = sum(1 for e in edges if e.type == EdgeType.RELATED_TO)
        if generic / len(edges) > 0.6:
            f.append(Finding("too_database_like",
                             f"{generic}/{len(edges)} edges are generic 'related_to'; "
                             "the graph is under-typed.", "medium"))
    return AuditReport(findings=f)


AUDIT_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"concern": {"type": "string"}, "detail": {"type": "string"},
                       "severity": {"type": "string", "enum": ["high", "medium", "low"]}},
        "required": ["concern", "detail", "severity"], "additionalProperties": False}}},
    "required": ["findings"], "additionalProperties": False,
}

_PROMPT = """You are auditing a computational World Model of scientific knowledge (a graph of
beliefs and typed relations). Given this summary, find weaknesses: does it really
LEARN (change beliefs with evidence) or is it a static database? Redundant relations?
Lost information? Absurd cycles? What still looks like a traditional database rather
than a living model? Return JSON only (findings: concern, detail, severity).

World Model summary:
{summary}"""


def codex_audit(wm: WorldModel, provider: Any) -> AuditReport:
    if not hasattr(provider, "complete_json"):
        return AuditReport()
    summary = {
        "stats": wm.stats(),
        "sample_beliefs": [
            {"label": n.label, "type": n.type.value, "confidence": n.confidence,
             "history_len": len(n.belief.get("history", []))}
            for n in wm.nodes() if n.type in BELIEF_TYPES][:15],
    }
    prompt = _PROMPT.format(summary=json.dumps(summary, default=str)[:6000])
    try:
        result = provider.complete_json(prompt, AUDIT_SCHEMA)
    except Exception as exc:  # noqa: BLE001
        return AuditReport([Finding("audit_error", str(exc), "low", source="codex")])
    return AuditReport([Finding(i.get("concern", "?"), i.get("detail", ""),
                                i.get("severity", "low"), source="codex")
                        for i in result.get("findings", [])])
