"""Research programs — the long-lived unit above individual hypotheses.

A ResearchProgram groups concepts, hypotheses, models, experiments, contradictions,
anomalies and open questions that persist across many investigations (years, not
one run).
"""

from __future__ import annotations

import statistics
from typing import Any

from .edges import EdgeType
from .graph import WorldModel
from .nodes import BELIEF_TYPES, NodeType, WorldNode


def create_program(wm: WorldModel, name: str, *, domain: str = "general",
                   description: str = "") -> WorldNode:
    return wm.create(NodeType.RESEARCH_PROGRAM, name, domain=domain,
                     description=description, data={"active": True})


def attach(wm: WorldModel, program_id: str, node_id: str) -> None:
    """Attach a node to a program (BELONGS_TO) and tag its program_id."""
    node = wm.get_node(node_id)
    if node is None:
        raise ValueError(f"node {node_id} not found")
    wm.link(EdgeType.BELONGS_TO, node_id, program_id)
    wm.update_node_data(node_id, {"program_id": program_id},
                        summary=f"attached to program {program_id}")


def program_members(wm: WorldModel, program_id: str) -> list[WorldNode]:
    ids = [e.source for e in wm.edges(target=program_id, etype=EdgeType.BELONGS_TO)]
    return [n for n in (wm.get_node(i) for i in ids) if n]


def program_summary(wm: WorldModel, program_id: str) -> dict[str, Any]:
    members = program_members(wm, program_id)
    by_type: dict[str, int] = {}
    for n in members:
        by_type[n.type.value] = by_type.get(n.type.value, 0) + 1
    belief_conf = [n.confidence for n in members if n.type in BELIEF_TYPES]
    open_contradictions = [n for n in members
                           if n.type == NodeType.CONTRADICTION and not n.data.get("resolved")]
    open_anomalies = [n for n in members
                      if n.type == NodeType.ANOMALY and not n.data.get("resolved")]
    open_questions = [n for n in members if n.type == NodeType.QUESTION]
    prog = wm.get_node(program_id)
    return {
        "program_id": program_id,
        "name": prog.label if prog else program_id,
        "n_members": len(members),
        "members_by_type": by_type,
        "mean_belief_confidence": round(statistics.mean(belief_conf), 4) if belief_conf else None,
        "open_contradictions": len(open_contradictions),
        "open_anomalies": len(open_anomalies),
        "open_questions": len(open_questions),
    }
