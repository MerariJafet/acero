"""Narrator — turns the World Model state into the sentences a scientist would say.

Satisfies the Sprint-8 "criterio final": ACERO should be able to say things like
"this hypothesis gained support because N independent experiments favoured it" or
"this theory now depends critically on an untested assumption". Every statement is
derived from the graph, with node ids for traceability.
"""

from __future__ import annotations

from typing import Any

from .edges import EdgeType
from .graph import WorldModel
from .nodes import BELIEF_TYPES, NodeType
from .queries import ScientificMemory


def narrate(wm: WorldModel) -> list[dict[str, Any]]:
    mem = ScientificMemory(wm)
    out: list[dict[str, Any]] = []

    # 1. Beliefs that gained support from independent replications.
    for n in wm.nodes():
        if n.type not in BELIEF_TYPES:
            continue
        reps = int(n.belief.get("replication_count", 0))
        support = mem.supporting_experiments(n.id)
        if reps >= 1 and n.confidence >= 0.5 and support:
            out.append({
                "kind": "gained_support",
                "text": f"'{n.label}' gained support because {len(support)} independent "
                        f"experiment(s) favoured it (confidence {n.confidence:.2f}, "
                        f"{reps} replications).",
                "node_id": n.id})

    # 2. Theories/models that depend critically on an untested assumption.
    for c in mem.critical_assumptions():
        out.append({
            "kind": "critical_untested_assumption",
            "text": f"'{c['dependents'][0]}' now depends critically on the assumption "
                    f"'{c['assumption']}', which has never been tested "
                    f"({c['n_dependents']} model(s) rely on it).",
            "assumption_id": c["assumption_id"]})

    # 3. Contradictions between research programs.
    contradictions = mem.open_contradictions()
    for con in contradictions:
        between = con.data.get("between", [])
        progs = set()
        for nid in between:
            node = wm.get_node(nid)
            if node and node.program_id:
                progs.add(node.program_id)
        if len(progs) >= 2:
            out.append({"kind": "cross_program_contradiction",
                        "text": f"There is a contradiction between two research programs: "
                                f"{con.label}.", "contradiction_id": con.id})

    # 4. Long-standing open anomalies.
    for a in mem.open_anomalies():
        out.append({"kind": "open_anomaly",
                    "text": f"The anomaly '{a.label}' remains unexplained.",
                    "anomaly_id": a.id})

    # 5. The next experiment that would resolve the most contradictions.
    best = _best_next_experiment(wm, mem)
    if best:
        out.append(best)

    return out


def _best_next_experiment(wm: WorldModel, mem: ScientificMemory) -> dict[str, Any] | None:
    """The experiment linked (via TESTS) to models involved in the most open
    contradictions has the highest resolving value."""
    open_contra = mem.open_contradictions()
    if not open_contra:
        return None
    involved: set[str] = set()
    for c in open_contra:
        involved.update(c.data.get("between", []))
    # Count, per experiment, how many involved models it tests.
    scores: dict[str, int] = {}
    for exp in wm.nodes(NodeType.EXPERIMENT):
        tested = {e.target for e in wm.edges(source=exp.id, etype=EdgeType.TESTS)}
        scores[exp.id] = len(tested & involved)
    if not scores or max(scores.values()) == 0:
        return None
    best_id = max(scores, key=lambda k: scores[k])
    best = wm.get_node(best_id)
    return {"kind": "highest_value_experiment",
            "text": f"The next experiment '{best.label if best else best_id}' has the highest "
                    f"scientific value because it bears on {scores[best_id]} model(s) "
                    f"involved in open contradictions.",
            "experiment_id": best_id}
