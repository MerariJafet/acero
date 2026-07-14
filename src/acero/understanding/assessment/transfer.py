"""Transfer assessment.

Real mastery requires using a concept in a DIFFERENT domain than it was learned in. A
transfer task presents a new context and grades whether the learner applies the concept
WITHOUT being shown the mapping. Passing a transfer task is the only evidence that yields
TRANSFER_CAPABLE / MASTERED.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import EvidenceType, UnderstandingEvidence
from .grading import GradeResult, build_evidence


@dataclass(frozen=True)
class TransferTask:
    concept: str
    source_domain: str
    target_domain: str
    task: str
    expected_elements: tuple[str, ...]
    forbidden_elements: tuple[str, ...] = ()


# Cross-domain transfer benchmark tasks (the mapping is deliberately NOT given).
TRANSFER_TASKS: tuple[TransferTask, ...] = (
    TransferTask(
        "identifiability", "harmonic oscillator", "logistic growth",
        "You fit logistic growth to data that never approaches the carrying capacity. "
        "Can you identify the carrying capacity K? Explain.",
        ("no", "not identifiable", "data does not constrain", "never reaches capacity"),
        ("K is uniquely determined",)),
    TransferTask(
        "diffusion", "thermal", "population",
        "A species spreads through a landscape the way heat spreads through a rod. "
        "What quantity plays the role of temperature, and what limits the analogy?",
        ("density", "concentration", "flux", "gradient", "regime"),
        ("identical physics",)),
    TransferTask(
        "overfitting", "curve fitting", "a new classifier",
        "A model scores 100% on its training set. Why is that not good news, and what "
        "would you check?",
        ("overfit", "held-out", "generalization", "test set"),
        ("100% means correct",)),
    TransferTask(
        "dimensional_analysis", "pendulum", "a new fluid problem",
        "Without deriving the equation, use units to guess how a drag force scales with "
        "velocity and fluid density. State what dimensional analysis cannot give you.",
        ("units", "scaling", "dimensionless", "cannot give the constant"),
        ("gives the exact coefficient",)),
)

_BY_CONCEPT = {t.concept: t for t in TRANSFER_TASKS}


def get_task(concept: str) -> TransferTask:
    if concept not in _BY_CONCEPT:
        raise KeyError(f"no transfer task for {concept!r}; have {sorted(_BY_CONCEPT)}")
    return _BY_CONCEPT[concept]


def assess_transfer(learner_id: str, concept: str, response: str, *,
                    confidence: float = 0.5, research_context: str | None = None
                    ) -> tuple[UnderstandingEvidence, GradeResult]:
    """Grade a transfer response as TRANSFER evidence."""
    task = get_task(concept)
    return build_evidence(
        learner_id, concept, EvidenceType.TRANSFER, task.task, response,
        list(task.expected_elements), confidence=confidence,
        research_context=research_context,
        forbidden_elements=list(task.forbidden_elements))
