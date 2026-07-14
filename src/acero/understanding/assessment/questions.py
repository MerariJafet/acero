"""Knowledge checks across Bloom levels.

Short, cumulative checks that distinguish recall / understanding / application /
analysis / evaluation / creation. Not multiple-choice only: each check names the
EvidenceType it elicits, so open-ended and executable tasks are first-class.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models import EvidenceType


class BloomLevel(str, Enum):
    RECALL = "recall"
    UNDERSTANDING = "understanding"
    APPLICATION = "application"
    ANALYSIS = "analysis"
    EVALUATION = "evaluation"
    CREATION = "creation"


@dataclass(frozen=True)
class KnowledgeCheck:
    concept: str
    bloom: BloomLevel
    evidence_type: EvidenceType
    prompt: str
    expected_elements: tuple[str, ...]


# Bloom level → the performance evidence it should elicit (never recall-only for the top).
_BLOOM_EVIDENCE: dict[BloomLevel, EvidenceType] = {
    BloomLevel.RECALL: EvidenceType.EXPLAIN_OWN_WORDS,
    BloomLevel.UNDERSTANDING: EvidenceType.EXPLAIN_OWN_WORDS,
    BloomLevel.APPLICATION: EvidenceType.SOLVE_SIMILAR,
    BloomLevel.ANALYSIS: EvidenceType.DETECT_ERROR,
    BloomLevel.EVALUATION: EvidenceType.COMPARE_MODELS,
    BloomLevel.CREATION: EvidenceType.PROPOSE_FALSIFICATION,
}


def evidence_for(bloom: BloomLevel) -> EvidenceType:
    return _BLOOM_EVIDENCE[bloom]


def check_for(concept: str, bloom: BloomLevel, prompt: str,
              expected_elements: list[str]) -> KnowledgeCheck:
    return KnowledgeCheck(concept, bloom, _BLOOM_EVIDENCE[bloom], prompt,
                          tuple(expected_elements))
