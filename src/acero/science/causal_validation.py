"""Substantive validation of causal DAGs — a well-drawn graph can be wrong.

The reviewer: the back-door criterion may be mathematically correct under an INCORRECT
DAG. CAUSA must separate formal validity from substantive validity. So each causal edge
carries its evidence (assumed / literature / experimental / expert-approved), and a DAG is
graded on five levels. Rule: a DAG whose edges were merely proposed by the LLM is NEVER
'substantively validated' — it can be syntactically valid and identifiable, but the claim
compiler must still refuse strong causal language until edges are justified by real
evidence or an expert signs off.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .causal import CausalGraph, Estimand, audit


class EdgeEvidence(IntEnum):
    ASSUMED = 0            # proposed by the LLM / analyst, no external support
    LITERATURE = 1         # supported by a cited source
    EXPERIMENTAL = 2       # supported by an interventional/quasi-experimental result
    EXPERT_APPROVED = 3    # a domain expert explicitly signed off


@dataclass
class CausalEdge:
    source: str
    target: str
    evidence: EdgeEvidence = EdgeEvidence.ASSUMED
    source_ref: str = ""          # DOI / citation / experiment id
    confidence: float = 0.0       # 0..1
    domain: str = ""
    temporal_ok: bool = True      # cause precedes effect
    reversible: bool = False      # could the arrow point the other way?
    approved_by: str = ""         # human expert, if any


class DagValidityLevel(IntEnum):
    INVALID = 0
    SYNTACTIC = 1          # acyclic, well-formed
    IDENTIFICATION = 2     # estimand identifiable under the DAG (back-door)
    SUBSTANTIVE = 3        # every edge justified beyond 'assumed'
    EXPERT_APPROVED = 4    # every key edge signed off by a human expert


@dataclass
class DagValidationReport:
    level: DagValidityLevel
    syntactic_ok: bool
    identifiable: bool
    substantive_ok: bool
    expert_approved: bool
    unjustified_edges: list[str]
    reversible_edges: list[str]

    @property
    def allows_causal_language(self) -> bool:
        """Strong causal language needs identification AND substantive justification —
        never an all-'assumed' AI DAG."""
        return self.level >= DagValidityLevel.SUBSTANTIVE

    def summary(self) -> dict[str, object]:
        return {
            "level": self.level.name,
            "identifiable": self.identifiable,
            "substantive_ok": self.substantive_ok,
            "expert_approved": self.expert_approved,
            "unjustified_edges": self.unjustified_edges,
            "reversible_edges": self.reversible_edges,
            "allows_causal_language": self.allows_causal_language,
        }


def validate_dag(graph: CausalGraph, edges: list[CausalEdge],
                 estimand: Estimand) -> DagValidationReport:
    syntactic_ok = not graph.has_cycle()
    verdict = audit(estimand, graph)
    identifiable = verdict.identifiable
    unjustified = [f"{e.source}->{e.target}" for e in edges
                   if e.evidence <= EdgeEvidence.ASSUMED]
    reversible = [f"{e.source}->{e.target}" for e in edges if e.reversible]
    substantive_ok = syntactic_ok and identifiable and not unjustified
    expert_approved = substantive_ok and all(
        e.evidence >= EdgeEvidence.EXPERT_APPROVED or e.approved_by for e in edges) \
        and bool(edges)

    if not syntactic_ok:
        level = DagValidityLevel.INVALID
    elif expert_approved:
        level = DagValidityLevel.EXPERT_APPROVED
    elif substantive_ok:
        level = DagValidityLevel.SUBSTANTIVE
    elif identifiable:
        level = DagValidityLevel.IDENTIFICATION
    else:
        level = DagValidityLevel.SYNTACTIC

    return DagValidationReport(level, syntactic_ok, identifiable, substantive_ok,
                               expert_approved, unjustified, reversible)
