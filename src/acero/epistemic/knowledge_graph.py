"""F9 — Epistemic knowledge graph: store not only WHAT we believe, but WHY, WHERE it could
fail, and WHAT we need to observe.

A self-contained typed graph (does not modify the existing world_model). Beliefs are
VERSIONED and never overwritten; edges are never deleted (weakened instead) — the same
invariants as ACERO's World Model. Node/relation types are those the reviewer requested,
so the graph can represent claims, assumptions, evidence, anomalies, contradictions,
boundaries, vulnerabilities, questions, rival hypotheses, predictions and discriminating
tests, plus unresolved disputes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.clock import now_iso


class NodeType(str, Enum):
    CLAIM = "claim"
    THEORY = "theory"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    EXPERIMENT = "experiment"
    OBSERVATION = "observation"
    ANOMALY = "anomaly"
    CONTRADICTION = "contradiction"
    BOUNDARY_CONDITION = "boundary_condition"
    ALTERNATIVE_EXPLANATION = "alternative_explanation"
    EPISTEMIC_VULNERABILITY = "epistemic_vulnerability"
    SCIENTIFIC_QUESTION = "scientific_question"
    HYPOTHESIS = "hypothesis"
    RIVAL_HYPOTHESIS = "rival_hypothesis"
    PREDICTION = "prediction"
    DISCRIMINATING_TEST = "discriminating_test"
    UNRESOLVED_DISPUTE = "unresolved_dispute"


class RelationType(str, Enum):
    DEPENDS_ON = "depends_on"          # CLAIM → ASSUMPTION
    SUPPORTS = "supports"              # EVIDENCE → CLAIM
    WEAKENS = "weakens"                # EVIDENCE → CLAIM
    TESTS = "tests"                    # EXPERIMENT/TEST → CLAIM/PREDICTION
    CONTRADICTS = "contradicts"        # ANOMALY → PREDICTION
    TARGETS = "targets"                # QUESTION → VULNERABILITY
    ANSWERS = "answers"                # HYPOTHESIS → QUESTION
    DISTINGUISHES = "distinguishes"    # PREDICTION/TEST → HYPOTHESIS
    VALID_WITHIN = "valid_within"      # THEORY → BOUNDARY_CONDITION
    DERIVED_FROM = "derived_from"      # DATASET/EVIDENCE → PROVENANCE_ROOT
    CONFLICTS_WITH = "conflicts_with"  # ANOMALY ↔ PREDICTION


@dataclass
class NodeVersion:
    version: int
    data: dict[str, Any]
    at: str


@dataclass
class Node:
    node_id: str
    type: NodeType
    history: list[NodeVersion] = field(default_factory=list)

    @property
    def current(self) -> dict[str, Any]:
        return self.history[-1].data if self.history else {}

    @property
    def version(self) -> int:
        return self.history[-1].version if self.history else 0


@dataclass
class Edge:
    src: str
    dst: str
    rel: RelationType
    weight: float = 1.0
    active: bool = True
    at: str = ""


class EpistemicKnowledgeGraph:
    """Typed, versioned graph. Beliefs never overwritten; edges weakened, never deleted."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []

    # --- nodes ---------------------------------------------------------------
    def upsert(self, node_id: str, ntype: NodeType, data: dict[str, Any]) -> Node:
        """Add a node or append a NEW version (never overwrite prior belief)."""
        n = self._nodes.get(node_id)
        if n is None:
            n = Node(node_id, ntype)
            self._nodes[node_id] = n
        n.history.append(NodeVersion(n.version + 1, dict(data), now_iso()))
        return n

    def get(self, node_id: str) -> Node | None:
        return self._nodes.get(node_id)

    def nodes_of(self, ntype: NodeType) -> list[Node]:
        return [n for n in self._nodes.values() if n.type == ntype]

    # --- edges ---------------------------------------------------------------
    def link(self, src: str, dst: str, rel: RelationType, weight: float = 1.0) -> Edge:
        e = Edge(src, dst, rel, weight, True, now_iso())
        self._edges.append(e)
        return e

    def weaken(self, src: str, dst: str, rel: RelationType) -> None:
        """Never delete a relation — weaken/deactivate it (World Model invariant)."""
        for e in self._edges:
            if e.src == src and e.dst == dst and e.rel == rel:
                e.active = False

    def out_edges(self, src: str, rel: RelationType | None = None) -> list[Edge]:
        return [e for e in self._edges if e.active and e.src == src
                and (rel is None or e.rel == rel)]

    def in_edges(self, dst: str, rel: RelationType | None = None) -> list[Edge]:
        return [e for e in self._edges if e.active and e.dst == dst
                and (rel is None or e.rel == rel)]

    # --- queries (why we believe / where it could fail) ---------------------
    def assumptions_of(self, claim_id: str) -> list[str]:
        return [e.dst for e in self.out_edges(claim_id, RelationType.DEPENDS_ON)]

    def evidence_for(self, claim_id: str) -> list[str]:
        return [e.src for e in self.in_edges(claim_id, RelationType.SUPPORTS)]

    def evidence_against(self, claim_id: str) -> list[str]:
        return [e.src for e in self.in_edges(claim_id, RelationType.WEAKENS)]

    def questions_targeting(self, vuln_id: str) -> list[str]:
        return [e.src for e in self.in_edges(vuln_id, RelationType.TARGETS)]

    def support_balance(self, claim_id: str) -> int:
        """Supporting minus weakening evidence lines (never a single 'trust score')."""
        return len(self.evidence_for(claim_id)) - len(self.evidence_against(claim_id))

    def summary(self) -> dict[str, object]:
        counts: dict[str, int] = {}
        for n in self._nodes.values():
            counts[n.type.value] = counts.get(n.type.value, 0) + 1
        return {"n_nodes": len(self._nodes),
                "n_edges": sum(1 for e in self._edges if e.active),
                "by_type": counts}
