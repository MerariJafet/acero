"""Aggregate the hybrid grader into a final, rule-governed grade.

Pipeline: deterministic rubric → forbidden claims → contradiction → consistency →
semantic advisory → evidence aggregation → grade + uncertainty + knowledge-state proposal.

Rules that hold ALWAYS:
- The deterministic layer is the authority; a hard fail (red flags / prohibited claims /
  self-contradiction) cannot be rescued by Codex.
- Codex can RAISE recognition of a valid paraphrase (lifting a deterministic near-miss to
  PASS_WITH_REVIEW) but can NEVER by itself elevate to MASTERED.
- A disagreement between layers is recorded, not hidden.
- If the semantic layer is unavailable, the deterministic result stands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .consistency import ConsistencyResult
from .consistency import check as consistency_check
from .contradiction import has_self_contradiction, prohibited_claims
from .deterministic import DeterministicResult
from .deterministic import evaluate as deterministic_eval
from .semantic import SemanticAssessment
from .semantic import assess as semantic_assess

PASS = 0.7


class GradeVerdict(str, Enum):
    PASS = "PASS"
    PASS_WITH_REVIEW = "PASS_WITH_REVIEW"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    HARD_FAIL = "HARD_FAIL"        # prohibited claim / contradiction — never rescued


@dataclass
class HybridGrade:
    verdict: GradeVerdict
    score: float
    uncertainty: float
    disagreement: bool
    deterministic_score: float
    semantic_available: bool
    prohibited: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    can_reach_mastery: bool = False        # Codex alone never sets this True
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"verdict": self.verdict.value, "score": self.score,
                "uncertainty": self.uncertainty, "disagreement": self.disagreement,
                "deterministic_score": self.deterministic_score,
                "semantic_available": self.semantic_available,
                "prohibited": self.prohibited, "reasons": self.reasons,
                "can_reach_mastery": self.can_reach_mastery,
                "provenance": self.provenance}


def aggregate(response: str, det: DeterministicResult, sem: SemanticAssessment | None,
              *, consistency: ConsistencyResult | None = None,
              learner_id: str = "grader") -> HybridGrade:
    reasons: list[str] = []
    prohibited = prohibited_claims(response, learner_id=learner_id)
    contradiction = has_self_contradiction(response)

    # 1. Hard fails: authority overrides everything, Codex cannot rescue.
    if prohibited:
        reasons.append(f"prohibited claim(s): {prohibited}")
        return HybridGrade(GradeVerdict.HARD_FAIL, 0.0, 0.0, False,
                           det.score, sem.available if sem else False,
                           prohibited=prohibited, reasons=reasons)
    if contradiction:
        reasons.append("self-contradiction detected")
        return HybridGrade(GradeVerdict.HARD_FAIL, 0.0, 0.0, False, det.score,
                           sem.available if sem else False, reasons=reasons)
    if det.red_flags:
        reasons.append(f"deterministic red flags: {det.red_flags}")
        return HybridGrade(GradeVerdict.HARD_FAIL, min(det.score, 0.3), 0.0, False,
                           det.score, sem.available if sem else False,
                           reasons=reasons)

    sem_available = bool(sem and sem.available)
    score = det.score
    verdict: GradeVerdict
    disagreement = False

    if not sem_available:
        reasons.append("semantic layer unavailable → deterministic result stands")
        verdict = (GradeVerdict.PASS if det.passed
                   else GradeVerdict.PARTIAL if det.score >= 0.4 else GradeVerdict.FAIL)
    else:
        assert sem is not None
        # semantic red flags reduce confidence but do not by themselves fail a passing det
        if sem.circular_reasoning:
            reasons.append("semantic: circular reasoning")
        if sem.unsupported_claim:
            reasons.append("semantic: unsupported claim")
        det_pass = det.passed
        sem_valid = sem.paraphrase_validity >= 0.6 and sem.conceptual_coherence >= 0.5
        # A STRONG paraphrase signal (no semantic red flags) may lift even a low-rubric
        # answer — but only to PASS_WITH_REVIEW (a human confirms), never to a clean PASS
        # or mastery. Codex-audit fix: the lift also requires a CITED fragment that
        # actually appears in the response, so Codex cannot lift on pure say-so.
        sem_strong = (sem.paraphrase_validity >= 0.75 and sem.conceptual_coherence >= 0.6
                      and not sem.circular_reasoning and not sem.contradiction
                      and not sem.unsupported_claim and bool(sem.cited_fragments))

        if det_pass and not sem_valid:
            disagreement = True
            reasons.append("deterministic PASS but semantic concern → PASS_WITH_REVIEW")
            verdict = GradeVerdict.PASS_WITH_REVIEW
        elif (not det_pass) and sem_strong and det.score > 0.1:
            # valid paraphrase the rubric missed: lift to review, NOT to pass/mastery
            disagreement = True
            reasons.append("deterministic near-miss but valid paraphrase → PASS_WITH_REVIEW")
            verdict = GradeVerdict.PASS_WITH_REVIEW
            score = max(score, 0.6)
        elif det_pass and sem_valid:
            verdict = GradeVerdict.PASS
        else:
            verdict = (GradeVerdict.PARTIAL if det.score >= 0.4 else GradeVerdict.FAIL)

    if consistency and consistency.repeats_prior:
        reasons.append("repeats a prior answer (low originality)")
        if verdict in (GradeVerdict.PASS, GradeVerdict.PASS_WITH_REVIEW):
            verdict = GradeVerdict.PASS_WITH_REVIEW
    if consistency and consistency.contradicts_prior:
        reasons.append("contradicts a prior well-evidenced answer")
        disagreement = True

    # uncertainty grows with disagreement and semantic unavailability
    uncertainty = round(0.1 + (0.3 if disagreement else 0.0)
                        + (0.2 if not sem_available else 0.0), 3)
    # Codex NEVER unlocks mastery: only a full deterministic pass may.
    can_reach_mastery = verdict == GradeVerdict.PASS and det.passed

    return HybridGrade(
        verdict=verdict, score=round(score, 4), uncertainty=uncertainty,
        disagreement=disagreement, deterministic_score=det.score,
        semantic_available=sem_available, reasons=reasons,
        can_reach_mastery=can_reach_mastery,
        provenance={"deterministic": det.score,
                    "semantic": sem.as_dict() if sem_available and sem else None})


def grade_hybrid(question: str, response: str, expected_elements: list[str], *,
                 required_concepts: list[str] | None = None,
                 forbidden_elements: list[str] | None = None,
                 prior_responses: list[str] | None = None,
                 provider: Any = None, learner_id: str = "grader") -> HybridGrade:
    """Full hybrid pipeline: deterministic (authority) → semantic advisory → aggregate."""
    det = deterministic_eval(response, expected_elements,
                             required_concepts=required_concepts,
                             forbidden_elements=forbidden_elements)
    sem = semantic_assess(question, expected_elements, response, provider)
    cons = (consistency_check(response, prior_responses or [])
            if prior_responses is not None else None)
    return aggregate(response, det, sem, consistency=cons, learner_id=learner_id)
