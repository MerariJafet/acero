"""The ReviewDossier: everything a human needs to review a claim, in one place.

It gathers the central claim, the main supporting AND counter evidence (with dependency
clustering so duplicated support is visible), the reliability card + readiness, the
comprehension status of the reviewer, the gate status, the limitations, the open questions,
and what still requires external validation. It states plainly what it is NOT: a discovery,
a publication, or an experimental validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..reliability.scorecard import PublicationCandidate, ReadinessLevel


@dataclass
class DossierEvidence:
    id: str
    summary: str
    stance: str                       # supporting | counter
    result_class: str = "SIMULATION"
    independent_group: str = ""
    limitations: list[str] = field(default_factory=list)


@dataclass
class ReviewDossier:
    id: str = field(default_factory=lambda: new_id("dossier"))
    project: str = ""
    central_claim: str = ""
    inference_level: str = "system_identification"
    supporting_evidence: list[DossierEvidence] = field(default_factory=list)
    counter_evidence: list[DossierEvidence] = field(default_factory=list)
    reliability_card: dict[str, Any] = field(default_factory=dict)
    readiness: str = ReadinessLevel.NOT_READY.value
    replication_status: str = "REEXECUTION"
    comprehension_status: str = "unknown"
    gate_status: str = "incomplete"
    limitations: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    required_external_review: bool = True
    unresolved_contradictions: int = 0
    created_at: str = field(default_factory=now_iso)

    # --- honesty: what this dossier is NOT ------------------------------
    def disclaimers(self) -> list[str]:
        return [
            "This is NOT a discovery: DISCOVERY_CONFIRMED is never granted.",
            "This is NOT a publication: nothing leaves the machine automatically.",
            "Computational results are NOT experimental validation.",
            f"The inference level is '{self.inference_level}' — a fitted equation is not a law.",
            "The human researcher is the author and the final scientific authority.",
        ]

    def independent_support_count(self) -> int:
        """Distinct independent groups among the supporting evidence (duplicates collapse)."""
        groups = {e.independent_group or e.id for e in self.supporting_evidence}
        return len(groups)

    def completeness(self) -> dict[str, bool]:
        """Which review-critical sections are present."""
        return {
            "has_central_claim": bool(self.central_claim),
            "has_supporting_evidence": bool(self.supporting_evidence),
            "has_counter_evidence": bool(self.counter_evidence),
            "has_reliability_card": bool(self.reliability_card),
            "has_limitations": bool(self.limitations),
            "has_open_questions": bool(self.open_questions),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "project": self.project, "central_claim": self.central_claim,
            "inference_level": self.inference_level,
            "supporting_evidence": [e.__dict__ for e in self.supporting_evidence],
            "counter_evidence": [e.__dict__ for e in self.counter_evidence],
            "independent_support_count": self.independent_support_count(),
            "readiness": self.readiness, "replication_status": self.replication_status,
            "comprehension_status": self.comprehension_status,
            "gate_status": self.gate_status, "limitations": self.limitations,
            "open_questions": self.open_questions,
            "unresolved_contradictions": self.unresolved_contradictions,
            "required_external_review": self.required_external_review,
            "reliability_card": self.reliability_card,
            "completeness": self.completeness(), "disclaimers": self.disclaimers(),
            "created_at": self.created_at,
        }


def from_candidate(candidate: PublicationCandidate, *, central_claim: str = "",
                   supporting: list[DossierEvidence] | None = None,
                   counter: list[DossierEvidence] | None = None,
                   limitations: list[str] | None = None,
                   open_questions: list[str] | None = None,
                   comprehension_status: str = "unknown") -> ReviewDossier:
    """Build a dossier from a Sprint-11 PublicationCandidate + the human-facing sections."""
    card = candidate.reliability_card.as_dict() if candidate.reliability_card else {}
    # Surface candidate blockers as open questions the human must weigh.
    questions = list(open_questions or [])
    questions += [f"blocker: {b}" for b in candidate.blockers]
    return ReviewDossier(
        project=candidate.project,
        central_claim=central_claim or candidate.central_claim,
        supporting_evidence=supporting or [],
        counter_evidence=counter or [],
        reliability_card=card, readiness=candidate.readiness.value,
        replication_status=candidate.replication_status,
        comprehension_status=comprehension_status,
        gate_status=candidate.gate_status,
        limitations=limitations or [], open_questions=questions,
        required_external_review=candidate.required_external_review)
