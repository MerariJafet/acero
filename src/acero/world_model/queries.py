"""Scientific memory: questions the World Model must be able to answer.

These are not chat; they are graph queries over beliefs and typed relations.
"""

from __future__ import annotations

from typing import Any

from .edges import EdgeType
from .graph import WorldModel
from .nodes import BELIEF_TYPES, NodeType, WorldNode


class ScientificMemory:
    def __init__(self, wm: WorldModel) -> None:
        self.wm = wm

    def _incoming(self, node_id: str, etype: EdgeType) -> list[WorldNode]:
        srcs = [e.source for e in self.wm.edges(target=node_id, etype=etype)]
        return [n for n in (self.wm.get_node(s) for s in srcs) if n]

    def _outgoing(self, node_id: str, etype: EdgeType) -> list[WorldNode]:
        tgts = [e.target for e in self.wm.edges(source=node_id, etype=etype)]
        return [n for n in (self.wm.get_node(t) for t in tgts) if n]

    def supporting_experiments(self, claim_id: str) -> list[WorldNode]:
        """Which experiments support this claim?"""
        supporters = self._incoming(claim_id, EdgeType.SUPPORTS) + self._incoming(claim_id, EdgeType.TESTS)
        return [n for n in supporters if n.type in {NodeType.EXPERIMENT, NodeType.EVIDENCE}]

    def contradicting_evidence(self, node_id: str) -> list[WorldNode]:
        """What evidence contradicts this belief?"""
        return self._incoming(node_id, EdgeType.CONTRADICTS) + self._incoming(node_id, EdgeType.INVALIDATES)

    def hypotheses_from(self, node_id: str) -> list[WorldNode]:
        """Which hypotheses arose from this node?"""
        out = self._outgoing(node_id, EdgeType.HYPOTHESIZES)
        out += [n for n in self._incoming(node_id, EdgeType.GENERATED_BY)
                if n.type == NodeType.HYPOTHESIS]
        return out

    def models_depending_on(self, assumption_id: str) -> list[WorldNode]:
        """Which models depend on this assumption?"""
        return [n for n in self._incoming(assumption_id, EdgeType.DEPENDS_ON)
                if n.type in {NodeType.MODEL, NodeType.THEORY, NodeType.LAW}]

    def research_using(self, node_id: str) -> list[WorldNode]:
        """Which experiments/models used this equation/dataset/tool?"""
        return (self._incoming(node_id, EdgeType.DERIVED_FROM)
                + self._incoming(node_id, EdgeType.REQUIRES)
                + self._incoming(node_id, EdgeType.COMPUTED_BY))

    def failed_experiments(self) -> list[WorldNode]:
        """What failed?"""
        return self.wm.nodes(NodeType.NEGATIVE_RESULT)

    def open_anomalies(self) -> list[WorldNode]:
        """Which anomalies remain unexplained?"""
        return [a for a in self.wm.nodes(NodeType.ANOMALY)
                if not a.data.get("resolved", False)]

    def open_contradictions(self) -> list[WorldNode]:
        return [c for c in self.wm.nodes(NodeType.CONTRADICTION)
                if not c.data.get("resolved", False)]

    def untested_beliefs(self) -> list[WorldNode]:
        """Which beliefs have never been put to the test?"""
        out = []
        for n in self.wm.nodes():
            if n.type in BELIEF_TYPES and not n.tested:
                if not self.supporting_experiments(n.id):
                    out.append(n)
        return out

    def weak_relations(self, threshold: float = 0.3) -> list[dict[str, Any]]:
        """Which relations are weak (low weight × confidence)?"""
        out = []
        for e in self.wm.edges():
            strength = e.weight * e.confidence
            if strength < threshold:
                out.append({"edge_id": e.id, "type": e.type.value,
                            "source": e.source, "target": e.target,
                            "strength": round(strength, 4)})
        return out

    def single_source_claims(self) -> list[WorldNode]:
        """Which claims rest on a single source?"""
        return [n for n in self.wm.nodes()
                if n.type in BELIEF_TYPES
                and n.belief.get("distinct_sources", 0) <= 1
                and n.belief.get("evidence_strength", 0) > 0]

    def critical_assumptions(self) -> list[dict[str, Any]]:
        """Assumptions that many models depend on but that were never tested."""
        out = []
        for a in self.wm.nodes(NodeType.ASSUMPTION):
            dependents = self.models_depending_on(a.id)
            if dependents and not a.tested:
                out.append({"assumption": a.label, "assumption_id": a.id,
                            "n_dependents": len(dependents),
                            "dependents": [d.label for d in dependents]})
        return sorted(out, key=lambda x: x["n_dependents"], reverse=True)

    def answer(self, question: str, node_id: str | None = None) -> dict[str, Any]:
        """Dispatch a natural-language-ish question to a structured query."""
        q = question.lower()
        if node_id and "support" in q:
            return {"supporting_experiments":
                    [n.label for n in self.supporting_experiments(node_id)]}
        if node_id and ("contradic" in q):
            return {"contradicting_evidence":
                    [n.label for n in self.contradicting_evidence(node_id)]}
        if "anomal" in q:
            return {"open_anomalies": [a.label for a in self.open_anomalies()]}
        if "untested" in q or "never" in q:
            return {"untested_beliefs": [n.label for n in self.untested_beliefs()]}
        if "weak" in q:
            return {"weak_relations": self.weak_relations()}
        if "single" in q or "one paper" in q:
            return {"single_source_claims": [n.label for n in self.single_source_claims()]}
        return {"error": "no structured query matched", "question": question}
