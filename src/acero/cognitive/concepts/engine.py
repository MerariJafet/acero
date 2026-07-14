"""Concept Engine (Sprint 8.5).

Persists scientific concepts as World-Model CONCEPT nodes (rich structure in the
node's ``data``), wires typed conceptual dependencies as edges, versions conceptual
transformations, computes a heuristic compression score, and answers conceptual
queries. Concepts proposed by Codex are stored with ``sources_verified=False`` and
are never accepted as evidence.
"""

from __future__ import annotations

from typing import Any

from ...world_model.edges import EdgeType
from ...world_model.graph import WorldModel
from ...world_model.nodes import NodeType, WorldNode
from .models import ConceptualTransformation, ScientificConcept
from .ontology import ACYCLIC, DEPENDENCY_EDGE


class CircularDependencyError(ValueError):
    """A conceptual dependency would create an illegal cycle."""


class ConceptEngine:
    def __init__(self, wm: WorldModel) -> None:
        self.wm = wm

    # ------------------------------------------------------------------ CRUD
    def create(self, concept: ScientificConcept) -> WorldNode:
        node = WorldNode(
            id=concept.id, project_id=self.wm.project_id, type=NodeType.CONCEPT,
            label=concept.canonical_name, domain=concept.domain,
            data={"concept": concept.model_dump(), "kind": "concept"})
        return self.wm.add_node(node)

    def get(self, concept_id: str) -> ScientificConcept | None:
        node = self.wm.get_node(concept_id)
        if node is None or node.type != NodeType.CONCEPT:
            return None
        return ScientificConcept(**node.data["concept"])

    def find(self, name: str) -> ScientificConcept | None:
        for node in self.wm.nodes(NodeType.CONCEPT):
            c = ScientificConcept(**node.data["concept"])
            if c.canonical_name.lower() == name.lower() or name.lower() in [
                    a.lower() for a in c.aliases]:
                return c
        return None

    def all_concepts(self) -> list[ScientificConcept]:
        return [ScientificConcept(**n.data["concept"]) for n in self.wm.nodes(NodeType.CONCEPT)]

    def _save(self, concept: ScientificConcept, *, summary: str) -> None:
        self.wm.update_node_data(concept.id, {"concept": concept.model_dump()},
                                 summary=summary)

    # ------------------------------------------------------------------ deps
    def add_dependency(self, source_id: str, target_id: str, dep: str) -> None:
        if dep not in DEPENDENCY_EDGE:
            raise ValueError(f"unknown dependency '{dep}'")
        if dep in ACYCLIC and self._would_cycle(source_id, target_id, dep):
            raise CircularDependencyError(
                f"'{dep}' {source_id}->{target_id} would create a cycle")
        self.wm.link(DEPENDENCY_EDGE[dep], source_id, target_id, confidence=0.6,
                     data={"dependency": dep})

    def _would_cycle(self, source_id: str, target_id: str, dep: str) -> bool:
        """Adding source->target: cycle if target already reaches source via same-kind edges."""
        etype = DEPENDENCY_EDGE[dep]
        seen: set[str] = set()
        stack = [target_id]
        while stack:
            cur = stack.pop()
            if cur == source_id:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(e.target for e in self.wm.edges(source=cur, etype=etype))
        return False

    def dependencies(self, concept_id: str, dep: str | None = None) -> list[dict[str, Any]]:
        out = []
        etypes = [DEPENDENCY_EDGE[dep]] if dep else list(DEPENDENCY_EDGE.values())
        for et in set(etypes):
            for e in self.wm.edges(source=concept_id, etype=et):
                tgt = self.wm.get_node(e.target)
                out.append({"dependency": et.value, "target_id": e.target,
                            "target": tgt.label if tgt else e.target})
        return out

    def depends_on_assumption(self, assumption: str) -> list[str]:
        """Which concepts list this assumption (would disappear if it were false)?"""
        return [c.canonical_name for c in self.all_concepts()
                if assumption.lower() in [a.lower() for a in c.assumptions]]

    def generalizes_of(self, concept_id: str) -> list[str]:
        return [self.wm.get_node(e.target).label  # type: ignore[union-attr]
                for e in self.wm.edges(source=concept_id, etype=EdgeType.GENERALIZES)
                if self.wm.get_node(e.target)]

    # ------------------------------------------------------------------ applicability
    def breaks_down_regimes(self, concept_id: str) -> list[dict[str, Any]]:
        c = self.get(concept_id)
        return [r.model_dump() for r in c.invalid_regimes] if c else []

    def is_applicable(self, concept_id: str, conditions: list[str]) -> dict[str, Any]:
        """A crude check: applicable unless any condition matches an invalid regime."""
        c = self.get(concept_id)
        if c is None:
            return {"applicable": False, "reason": "unknown concept"}
        invalid_hits = []
        for r in c.invalid_regimes:
            for cond in conditions:
                if any(cond.lower() in inv.lower() or inv.lower() in cond.lower()
                       for inv in r.invalid_conditions):
                    invalid_hits.append(r.label)
        return {"applicable": not invalid_hits, "invalid_regimes_hit": invalid_hits}

    # ------------------------------------------------------------------ transformations
    def transform(self, concept_id: str, transformation: ConceptualTransformation
                  ) -> ScientificConcept:
        """Record a conceptual transformation (versioned; previous rep NOT deleted)."""
        c = self.get(concept_id)
        if c is None:
            raise ValueError(f"unknown concept {concept_id}")
        c.historical_versions.append(transformation)
        self._save(c, summary=f"transformation: {transformation.previous_model} -> "
                              f"{transformation.new_model}")
        return c

    # ------------------------------------------------------------------ compression
    def compression_score(self, concept_id: str, *, phenomena_explained: int = 0,
                          rules_replaced: int = 0, new_predictions: int = 0,
                          exceptions: int = 0) -> dict[str, Any]:
        """Heuristic conceptual compression (configurable, explainable — NOT truth).

        score = (phenomena + rules_replaced + new_predictions) / (assumptions + exceptions + 1)
        """
        c = self.get(concept_id)
        if c is None:
            raise ValueError(f"unknown concept {concept_id}")
        n_assumptions = len(c.assumptions)
        numerator = phenomena_explained + rules_replaced + new_predictions
        denom = n_assumptions + exceptions + 1
        return {"compression_score": round(numerator / denom, 4),
                "phenomena_explained": phenomena_explained, "rules_replaced": rules_replaced,
                "new_predictions": new_predictions, "assumptions": n_assumptions,
                "exceptions": exceptions,
                "note": "heuristic, configurable; not a scientific measure of truth"}

    # ------------------------------------------------------------------ compare
    def compare(self, id_a: str, id_b: str) -> dict[str, Any]:
        a, b = self.get(id_a), self.get(id_b)
        if a is None or b is None:
            raise ValueError("both concepts must exist")
        shared_inv = set(a.invariants) & set(b.invariants)
        shared_sym = set(a.symmetries) & set(b.symmetries)
        shared_vars = set(a.variables) & set(b.variables)
        same_dims = a.dimensions == b.dimensions and bool(a.dimensions)
        return {"shared_invariants": sorted(shared_inv), "shared_symmetries": sorted(shared_sym),
                "shared_variables": sorted(shared_vars), "same_dimensions": same_dims,
                "same_type": a.concept_type == b.concept_type}

    # ------------------------------------------------------------------ integrity
    def unverified_concepts(self) -> list[str]:
        return [c.canonical_name for c in self.all_concepts()
                if c.generator == "codex" and not c.sources_verified]
