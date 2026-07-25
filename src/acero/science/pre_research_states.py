"""Pre-research state ladder — from a human topic to a research-ready question.

The reviewer's integrated flow starts BEFORE a hypothesis exists: a general topic must
become a map of claims, a vulnerability surface, prioritized questions, rival hypotheses
and a discriminating test — and only THEN enter the exploratory regime. The system must
NOT jump from a general topic straight to a confirmatory experiment.

This ladder feeds into the constitution's ScientificState (which starts at IDEA /
HIPOTESIS_EXPLORATORIA). `READY_FOR_EXPLORATORY_RESEARCH` is the hand-off point.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PreResearchState(IntEnum):
    TOPIC_RECEIVED = 0
    KNOWLEDGE_MAPPED = 1
    CLAIMS_RECONSTRUCTED = 2
    VULNERABILITIES_IDENTIFIED = 3
    QUESTIONS_GENERATED = 4
    QUESTIONS_PRIORITIZED = 5
    RIVAL_HYPOTHESES_DEFINED = 6
    DISCRIMINATING_TEST_DESIGNED = 7
    READY_FOR_EXPLORATORY_RESEARCH = 8


@dataclass
class PreResearchEvidence:
    knowledge_mapped: bool = False
    claims_reconstructed: bool = False
    vulnerabilities_identified: bool = False
    questions_generated: bool = False
    questions_prioritized: bool = False
    rival_hypotheses_defined: bool = False
    discriminating_test_designed: bool = False


_GUARD = {
    PreResearchState.KNOWLEDGE_MAPPED: "knowledge_mapped",
    PreResearchState.CLAIMS_RECONSTRUCTED: "claims_reconstructed",
    PreResearchState.VULNERABILITIES_IDENTIFIED: "vulnerabilities_identified",
    PreResearchState.QUESTIONS_GENERATED: "questions_generated",
    PreResearchState.QUESTIONS_PRIORITIZED: "questions_prioritized",
    PreResearchState.RIVAL_HYPOTHESES_DEFINED: "rival_hypotheses_defined",
    PreResearchState.DISCRIMINATING_TEST_DESIGNED: "discriminating_test_designed",
}


def max_reachable(ev: PreResearchEvidence) -> PreResearchState:
    state = PreResearchState.TOPIC_RECEIVED
    for rung in list(PreResearchState)[1:8]:
        if getattr(ev, _GUARD[rung]):
            state = rung
        else:
            return state
    return PreResearchState.READY_FOR_EXPLORATORY_RESEARCH


def ready_for_exploratory(ev: PreResearchEvidence) -> bool:
    """Only when a topic has been turned into a discriminating test may exploratory
    research begin. A general topic can never jump straight to a confirmatory experiment."""
    return max_reachable(ev) is PreResearchState.READY_FOR_EXPLORATORY_RESEARCH


def next_required(ev: PreResearchEvidence) -> str:
    cur = max_reachable(ev)
    if cur is PreResearchState.READY_FOR_EXPLORATORY_RESEARCH:
        return "listo: entra al régimen exploratorio de la Constitución"
    return _GUARD[PreResearchState(cur + 1)]
