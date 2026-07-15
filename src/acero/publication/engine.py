"""Publication preparation orchestrator (Sprint 12).

Ties the Sprint-11 reliability assessment → a ReviewDossier → a human review → a gated local
export. It never publishes; the strongest outcome is a locally exported package approved for
external human scientific review.
"""

from __future__ import annotations

from typing import Any

from ..reliability.engine import run_reliability
from ..reliability.scorecard import PublicationCandidate, ScientificReliabilityCard
from .dossier import DossierEvidence, ReviewDossier, from_candidate
from .export import evaluate_export
from .review import HumanReviewSession, ReviewDecision


def build_dossier(project: str, central_claim: str, *,
                  reproducibility: float = 0.9, calibration: float = 0.8,
                  evidence_independence: float = 0.8, human_understanding: float = 0.9,
                  provenance: float = 0.9, externally_validated: bool = False,
                  unresolved_contradictions: int = 0,
                  supporting: list[DossierEvidence] | None = None,
                  counter: list[DossierEvidence] | None = None,
                  limitations: list[str] | None = None,
                  open_questions: list[str] | None = None) -> ReviewDossier:
    r = run_reliability(project, reproducibility=reproducibility, calibration=calibration,
                        evidence_independence=evidence_independence,
                        human_understanding=human_understanding, provenance=provenance,
                        externally_validated=externally_validated,
                        unresolved_contradictions=unresolved_contradictions)
    # rebuild a candidate carrying the card (run_reliability returns dicts)
    card = ScientificReliabilityCard(subject=project)
    for name, dim in r["card"]["dimensions"].items():
        card.set(name, dim["measurement"], dim["sample"], limitation=dim["limitation"],
                 trend=dim["trend"], threshold=dim["threshold"])
    pc = PublicationCandidate(project=project, central_claim=central_claim,
                              reliability_card=card)
    pc.evaluate(gate_complete=True, human_understands=human_understanding >= 0.7,
                externally_validated=externally_validated,
                unresolved_contradictions=unresolved_contradictions)
    dossier = from_candidate(
        pc, central_claim=central_claim, supporting=supporting, counter=counter,
        limitations=limitations, open_questions=open_questions,
        comprehension_status="sufficient" if human_understanding >= 0.7 else "insufficient")
    dossier.unresolved_contradictions = unresolved_contradictions
    return dossier


def full_review(project: str, central_claim: str, reviewer: str, *,
                limitations: list[str] | None = None, **kw: Any
                ) -> tuple[ReviewDossier, HumanReviewSession, dict[str, Any]]:
    """Build a dossier, run a (fully-acknowledged) human review, and evaluate export."""
    dossier = build_dossier(project, central_claim, limitations=limitations or ["computational only"],
                            **kw)
    review = HumanReviewSession(dossier_id=dossier.id, reviewer=reviewer,
                               comprehension_ok=dossier.comprehension_status == "sufficient")
    for section in ("central_claim", "main_evidence", "main_counter_evidence",
                    "limitations", "reliability", "what_remains_to_validate_externally"):
        review.acknowledge(section)
    try:
        review.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=dossier, reasons=["reviewed; evidence and limitations understood"])
    except Exception:  # noqa: BLE001 - approval refused → record as request-changes
        review.record(ReviewDecision.REQUEST_CHANGES, dossier=dossier,
                      reasons=["preconditions not met"])
    decision = evaluate_export(dossier, review)
    return dossier, review, decision.as_dict()
