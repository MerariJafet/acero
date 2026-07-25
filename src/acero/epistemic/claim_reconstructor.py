"""ClaimReconstructor — understand a claim BEFORE criticizing it.

The reviewer's first discipline (charitable interpretation): EVA must reconstruct the
strongest version of a claim before attacking it. So the first step is not critique but
comprehension — extract exactly what a theory/paper/consensus asserts, under what
conditions, with what evidence, and what it does NOT assert.

The reconstruction is a structured `ClaimRecord`. It can be built from explicit fields
(deterministic, testable) or extracted by an LLM (optional, injected). The record is the
input to EVA and to the evidence-lineage / independence machinery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EvidenceType(str, Enum):
    OBSERVATIONAL = "observational"
    PREDICTIVE = "predictive"
    EXPERIMENTAL = "experimental"
    CAUSAL_DESIGN = "causal_design"
    META_ANALYSIS = "meta_analysis"
    THEORETICAL = "theoretical"
    UNKNOWN = "unknown"


class ReplicationStatus(str, Enum):
    NONE = "none"
    INTERNAL_ONLY = "internal_only"       # re-run / holdout of the same data
    INDEPENDENT = "independent"           # a genuinely independent dataset
    CONTESTED = "contested"               # replications disagree


@dataclass
class ClaimRecord:
    """The reconstructed, normalized content of a scientific claim."""
    claim_id: str
    claim_text: str
    normalized_claim: str = ""
    population_or_domain: str = ""
    exposure_or_input: str = ""
    outcome_or_prediction: str = ""
    conditions: str = ""
    effect_direction: str = ""
    effect_size: str = ""
    evidence_type: EvidenceType = EvidenceType.UNKNOWN
    supporting_sources: tuple[str, ...] = ()
    contradicting_sources: tuple[str, ...] = ()
    validation_methods: tuple[str, ...] = ()
    replication_status: ReplicationStatus = ReplicationStatus.NONE
    boundary_conditions: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    mechanism: str = ""
    provenance_roots: tuple[str, ...] = ()     # distinct curation roots of the evidence
    uncertainty: float = 0.5                   # 0 (certain) … 1 (very uncertain)

    def n_independent_sources(self) -> int:
        """Distinct provenance roots — five papers from one root are one evidence line."""
        return len(set(self.provenance_roots)) if self.provenance_roots \
            else len(set(self.supporting_sources))

    def summary(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "normalized": self.normalized_claim or self.claim_text[:120],
            "evidence_type": self.evidence_type.value,
            "replication": self.replication_status.value,
            "n_independent_sources": self.n_independent_sources(),
            "n_assumptions": len(self.assumptions),
            "has_mechanism": bool(self.mechanism),
            "has_boundaries": bool(self.boundary_conditions),
        }


@dataclass
class ReconstructionRequest:
    topic: str
    raw_text: str = ""
    known_fields: dict = field(default_factory=dict)


def reconstruct_claim(request: ReconstructionRequest, claim_id: str = "claim") -> ClaimRecord:
    """Deterministic reconstruction from explicit fields (the 'understand' step). An LLM
    extractor can populate `known_fields`; here we assemble and normalize, not critique."""
    f = request.known_fields
    def g(k, default=""):
        return f.get(k, default)
    ev = f.get("evidence_type", EvidenceType.UNKNOWN)
    ev = ev if isinstance(ev, EvidenceType) else EvidenceType(str(ev))
    rep = f.get("replication_status", ReplicationStatus.NONE)
    rep = rep if isinstance(rep, ReplicationStatus) else ReplicationStatus(str(rep))
    return ClaimRecord(
        claim_id=claim_id,
        claim_text=request.raw_text or str(g("claim_text", request.topic)),
        normalized_claim=str(g("normalized_claim", "")),
        population_or_domain=str(g("population_or_domain", "")),
        exposure_or_input=str(g("exposure_or_input", "")),
        outcome_or_prediction=str(g("outcome_or_prediction", "")),
        conditions=str(g("conditions", "")),
        effect_direction=str(g("effect_direction", "")),
        effect_size=str(g("effect_size", "")),
        evidence_type=ev,
        supporting_sources=tuple(g("supporting_sources", ()) or ()),
        contradicting_sources=tuple(g("contradicting_sources", ()) or ()),
        validation_methods=tuple(g("validation_methods", ()) or ()),
        replication_status=rep,
        boundary_conditions=tuple(g("boundary_conditions", ()) or ()),
        assumptions=tuple(g("assumptions", ()) or ()),
        mechanism=str(g("mechanism", "")),
        provenance_roots=tuple(g("provenance_roots", ()) or ()),
        uncertainty=float(g("uncertainty", 0.5)),
    )
