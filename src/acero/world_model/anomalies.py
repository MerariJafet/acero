"""Anomaly engine.

When an experiment produces something unexpected, an Anomaly node is created
recording what the system expected, what happened, which hypotheses might explain
it, and which future research should resolve it. Anomalies are NEVER deleted; they
persist until explicitly resolved with an explanation.
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..provenance.events import ProvenanceAction
from .edges import EdgeType
from .graph import WorldModel
from .nodes import NodeType, WorldNode


def register_anomaly(wm: WorldModel, *, label: str, expected: Any, observed: Any,
                     experiment_id: str | None = None, domain: str = "general",
                     candidate_explanations: list[str] | None = None,
                     actor: str = "system") -> WorldNode:
    node = wm.create(
        NodeType.ANOMALY, label, domain=domain,
        data={"expected": expected, "observed": observed,
              "candidate_explanations": candidate_explanations or [],
              "resolved": False, "registered_at": now_iso(),
              "future_research": "Design a discriminating experiment for the candidate explanations."})
    if experiment_id and wm.get_node(experiment_id):
        wm.link(EdgeType.OBSERVED_IN, node.id, experiment_id)
    # Each candidate explanation becomes a Hypothesis node linked to the anomaly.
    for expl in (candidate_explanations or []):
        h = wm.create(NodeType.HYPOTHESIS, expl, domain=domain,
                      data={"explains_anomaly": node.id})
        wm.link(EdgeType.EXPLAINS, h.id, node.id, confidence=0.3)
    # Opening an OpenProblem keeps the anomaly on the agenda.
    problem = wm.create(NodeType.OPEN_PROBLEM, f"Explain anomaly: {label}", domain=domain,
                        data={"anomaly_id": node.id, "resolved": False})
    wm.link(EdgeType.RELATED_TO, problem.id, node.id)
    wm.ledger.record_event(wm.project_id, ProvenanceAction.CREATE, actor,
                           f"anomaly registered: {label}", {"resolved": False},
                           entity_id=node.id)
    return node


def resolve_anomaly(wm: WorldModel, anomaly_id: str, explanation: str,
                    *, actor: str = "human") -> None:
    node = wm.get_node(anomaly_id)
    if node is None or node.type != NodeType.ANOMALY:
        raise ValueError(f"{anomaly_id} is not an anomaly node")
    wm.update_node_data(anomaly_id,
                        {"resolved": True, "resolution": explanation, "resolved_at": now_iso()},
                        summary=f"anomaly resolved: {explanation[:60]}", actor=actor)
