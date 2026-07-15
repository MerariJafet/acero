"""Evidence dependency, replication level, and multidimensional quality (Sprint 11).

Two pieces of evidence are NOT independent when they share a dataset, sample, pipeline,
simulator, generating model, derived source, or systematic error. Dependent evidence must
never be counted as independent replication, and a re-execution with the same seed is not a
scientific replication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DependencyType(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    SAME_DATASET = "SAME_DATASET"
    SAME_SAMPLE = "SAME_SAMPLE"
    SAME_PIPELINE = "SAME_PIPELINE"
    SAME_SIMULATOR = "SAME_SIMULATOR"
    DERIVED_SOURCE = "DERIVED_SOURCE"
    SHARED_SYSTEMATIC = "SHARED_SYSTEMATIC"
    UNKNOWN_DEPENDENCY = "UNKNOWN_DEPENDENCY"


# How strongly each dependency type collapses independent count (1.0 = fully dependent).
_STRENGTH: dict[DependencyType, float] = {
    DependencyType.INDEPENDENT: 0.0,
    DependencyType.SAME_DATASET: 0.9,
    DependencyType.SAME_SAMPLE: 0.95,
    DependencyType.SAME_PIPELINE: 0.8,
    DependencyType.SAME_SIMULATOR: 0.85,
    DependencyType.DERIVED_SOURCE: 0.9,
    DependencyType.SHARED_SYSTEMATIC: 0.7,
    DependencyType.UNKNOWN_DEPENDENCY: 0.5,
}


class ReplicationLevel(str, Enum):
    REEXECUTION = "REEXECUTION"                       # same seed/code/env — NOT replication
    COMPUTATIONAL_REPRODUCTION = "COMPUTATIONAL_REPRODUCTION"
    DIRECT_REPLICATION = "DIRECT_REPLICATION"
    CONCEPTUAL_REPLICATION = "CONCEPTUAL_REPLICATION"
    EXTERNAL_VALIDATION = "EXTERNAL_VALIDATION"
    CROSS_DOMAIN_VALIDATION = "CROSS_DOMAIN_VALIDATION"


INDEPENDENT_REPLICATION_LEVELS = frozenset({
    ReplicationLevel.DIRECT_REPLICATION, ReplicationLevel.CONCEPTUAL_REPLICATION,
    ReplicationLevel.EXTERNAL_VALIDATION, ReplicationLevel.CROSS_DOMAIN_VALIDATION,
})


@dataclass
class Evidence:
    """A minimal evidence descriptor with the fingerprints that reveal dependence."""

    id: str
    dataset: str | None = None
    sample: str | None = None
    pipeline: str | None = None
    simulator: str | None = None
    source_paper: str | None = None
    derived_from: str | None = None       # id of evidence this was derived from
    seed: int | None = None
    systematic: str | None = None         # shared systematic-error tag
    analyst: str | None = None            # shared human analyst/team (methodological dep.)
    method: str | None = None             # shared methodological choice


@dataclass
class EvidenceDependency:
    evidence_a: str
    evidence_b: str
    dependency_type: DependencyType
    shared_origin: str
    estimated_strength: float
    rationale: str
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"evidence_a": self.evidence_a, "evidence_b": self.evidence_b,
                "dependency_type": self.dependency_type.value,
                "shared_origin": self.shared_origin,
                "estimated_strength": self.estimated_strength,
                "rationale": self.rationale, "provenance": self.provenance}


def classify_pair(a: Evidence, b: Evidence) -> EvidenceDependency:
    """Determine the dependency between two evidence items (strongest match wins)."""
    checks: list[tuple[DependencyType, str | None, str | None, str]] = [
        (DependencyType.SAME_SAMPLE, a.sample, b.sample, "same sample"),
        (DependencyType.SAME_DATASET, a.dataset, b.dataset, "same dataset"),
        (DependencyType.SAME_SIMULATOR, a.simulator, b.simulator, "same simulator"),
        (DependencyType.SAME_PIPELINE, a.pipeline, b.pipeline, "same pipeline/code"),
        (DependencyType.SHARED_SYSTEMATIC, a.systematic, b.systematic,
         "shared systematic error"),
        # shared human analyst/team or methodological choice is a dependence too
        # (Codex-audit fix): correlated human judgement is not independent evidence.
        (DependencyType.SHARED_SYSTEMATIC, a.analyst, b.analyst, "same analyst/team"),
        (DependencyType.SHARED_SYSTEMATIC, a.method, b.method, "same methodological choice"),
    ]
    for dtype, va, vb, why in checks:
        if va is not None and va == vb:
            return EvidenceDependency(a.id, b.id, dtype, str(va),
                                      _STRENGTH[dtype], why)
    # derived source (one cites/derives from the other or a common paper)
    if a.derived_from == b.id or b.derived_from == a.id:
        return EvidenceDependency(a.id, b.id, DependencyType.DERIVED_SOURCE,
                                  "derivation", _STRENGTH[DependencyType.DERIVED_SOURCE],
                                  "one evidence derived from the other")
    if a.source_paper is not None and a.source_paper == b.source_paper:
        return EvidenceDependency(a.id, b.id, DependencyType.DERIVED_SOURCE,
                                  str(a.source_paper),
                                  _STRENGTH[DependencyType.DERIVED_SOURCE],
                                  "same source paper")
    return EvidenceDependency(a.id, b.id, DependencyType.INDEPENDENT, "", 0.0,
                              "no shared origin detected")


@dataclass
class DependencyGraph:
    evidence: dict[str, Evidence] = field(default_factory=dict)
    dependencies: list[EvidenceDependency] = field(default_factory=list)

    def add(self, ev: Evidence) -> None:
        self.evidence[ev.id] = ev

    def build(self) -> list[EvidenceDependency]:
        ids = list(self.evidence)
        self.dependencies = []
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                dep = classify_pair(self.evidence[ids[i]], self.evidence[ids[j]])
                if dep.dependency_type != DependencyType.INDEPENDENT:
                    self.dependencies.append(dep)
        return self.dependencies

    def clusters(self) -> list[list[str]]:
        """Union-find clusters of dependent evidence (each cluster ≈ one effective sample)."""
        parent: dict[str, str] = {e: e for e in self.evidence}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for dep in self.dependencies:
            ra, rb = find(dep.evidence_a), find(dep.evidence_b)
            if ra != rb:
                parent[ra] = rb
        groups: dict[str, list[str]] = {}
        for e in self.evidence:
            groups.setdefault(find(e), []).append(e)
        return [sorted(g) for g in groups.values()]

    def effective_independent_count(self) -> int:
        """Number of INDEPENDENT evidence groups — dependent items collapse to one."""
        if not self.dependencies:
            self.build()
        return len(self.clusters())

    def counts_as_replication(self, level: ReplicationLevel) -> bool:
        return level in INDEPENDENT_REPLICATION_LEVELS


@dataclass
class EvidenceQuality:
    """Multidimensional quality — never silently collapsed into one number."""

    provenance_quality: float = 0.0
    measurement_quality: float = 0.0
    design_quality: float = 0.0
    reproducibility: float = 0.0
    independence: float = 0.0
    sample_adequacy: float = 0.0
    calibration: float = 0.0
    external_validity: float = 0.0
    methodological_transparency: float = 0.0
    contradiction_status: str = "none"          # none | open | resolved

    def components(self) -> dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if isinstance(v, float)}

    def aggregate(self) -> float:
        """A view, not a verdict — the mean of the numeric components."""
        comps = self.components()
        return round(sum(comps.values()) / len(comps), 4) if comps else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {**self.components(), "contradiction_status": self.contradiction_status,
                "aggregate_view": self.aggregate()}


def dependency_aware_support(graph: DependencyGraph, per_item_support: float = 0.2,
                             *, max_confidence: float = 0.99) -> dict[str, Any]:
    """Combine evidence into a support figure that respects dependence.

    Naively, N items give N·support; but dependent items collapse to their cluster count,
    so duplicated evidence does not inflate support. Confidence never reaches 1.
    """
    n_items = len(graph.evidence)
    n_independent = graph.effective_independent_count()
    naive = min(max_confidence, per_item_support * n_items)
    honest = min(max_confidence, per_item_support * n_independent)
    return {"n_items": n_items, "n_independent_groups": n_independent,
            "naive_support": round(naive, 4), "dependency_aware_support": round(honest, 4),
            "inflation_avoided": round(naive - honest, 4),
            "clusters": graph.clusters()}
