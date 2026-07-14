"""Contradiction engine.

Automatically detects incompatible beliefs (claims, models, predictions, results,
assumptions) and, for each, creates a Contradiction node AND opens a new research
Question. Detection is structural: belief nodes carry ``data['subject']`` and
``data['stance']``; a configurable table says which stances are incompatible.
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from .edges import EdgeType
from .graph import WorldModel
from .nodes import BELIEF_TYPES, NodeType

# Configurable incompatibility table (stance pairs that cannot both hold).
INCOMPATIBLE_STANCES: set[frozenset[str]] = {
    frozenset({"increases", "decreases"}),
    frozenset({"exists", "not_exists"}),
    frozenset({"linear", "exponential"}),
    frozenset({"monotonic", "oscillatory"}),
    frozenset({"causal", "spurious"}),
    frozenset({"holds", "violated"}),
}


def _incompatible(a: str, b: str) -> bool:
    return frozenset({a, b}) in INCOMPATIBLE_STANCES


def _already_linked(wm: WorldModel, n1: str, n2: str) -> bool:
    for c in wm.nodes(NodeType.CONTRADICTION):
        pair = set(c.data.get("between", []))
        if {n1, n2} == pair:
            return True
    return False


def detect_contradictions(wm: WorldModel, *, actor: str = "system") -> list[dict[str, Any]]:
    """Scan belief nodes; create Contradiction + Question for each new incompatibility."""
    beliefs = [n for n in wm.nodes() if n.type in BELIEF_TYPES
               and n.data.get("subject") and n.data.get("stance")]
    by_subject: dict[str, list] = {}
    for n in beliefs:
        by_subject.setdefault(str(n.data["subject"]).lower(), []).append(n)

    created: list[dict[str, Any]] = []
    for subject, group in by_subject.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if not _incompatible(str(a.data["stance"]), str(b.data["stance"])):
                    continue
                if _already_linked(wm, a.id, b.id):
                    continue
                contra = wm.create(
                    NodeType.CONTRADICTION,
                    f"Contradiction on '{subject}': {a.data['stance']} vs {b.data['stance']}",
                    domain=a.domain,
                    data={"between": [a.id, b.id], "subject": subject,
                          "stances": [a.data["stance"], b.data["stance"]],
                          "resolved": False, "detected_at": now_iso()})
                wm.link(EdgeType.CONTRADICTS, a.id, b.id, weight=1.0, confidence=0.9)
                wm.link(EdgeType.RELATED_TO, contra.id, a.id)
                wm.link(EdgeType.RELATED_TO, contra.id, b.id)
                # Opening a new research question is mandatory.
                question = wm.create(
                    NodeType.QUESTION,
                    f"Why do '{a.label}' and '{b.label}' disagree about {subject}?",
                    domain=a.domain, data={"opened_by": contra.id})
                wm.link(EdgeType.GENERATED_BY, question.id, contra.id)
                # Both beliefs take a contradiction penalty.
                wm.update_belief(a.id, event="contradiction", contradiction=1,
                                 open_question=1, source=contra.id, actor=actor)
                wm.update_belief(b.id, event="contradiction", contradiction=1,
                                 open_question=1, source=contra.id, actor=actor)
                created.append({"contradiction_id": contra.id, "question_id": question.id,
                                "between": [a.label, b.label], "subject": subject})
    return created


def resolve_contradiction(wm: WorldModel, contradiction_id: str, explanation: str,
                          *, actor: str = "human") -> None:
    node = wm.get_node(contradiction_id)
    if node is None or node.type != NodeType.CONTRADICTION:
        raise ValueError(f"{contradiction_id} is not a contradiction node")
    wm.update_node_data(
        contradiction_id,
        {"resolved": True, "resolution": explanation, "resolved_at": now_iso()},
        summary=f"contradiction resolved: {explanation[:60]}", actor=actor)
