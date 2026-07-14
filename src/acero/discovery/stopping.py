"""Stopping rules for the discovery loop (Sprint 6.6).

Produces an explicit decision — CONTINUE / REFINE / PAUSE / STOP / ESCALATE_TO_HUMAN
— from an auditable set of conditions. No silent infinite loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StopDecision(str, Enum):
    CONTINUE = "CONTINUE"
    REFINE = "REFINE"
    PAUSE = "PAUSE"
    STOP = "STOP"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"


@dataclass
class DiscoveryState:
    budget_spent: float = 0.0
    budget_total: float = 1.0
    rounds: int = 0
    max_rounds: int = 20
    last_improvement: float = 1.0        # improvement in best metric last round
    min_improvement: float = 0.01
    inconclusive_streak: int = 0
    max_inconclusive: int = 3
    dominated_hypotheses: int = 0
    total_hypotheses: int = 1
    high_prior_sensitivity: bool = False
    has_discriminating_experiment: bool = True
    data_missing: bool = False
    risk_exceeds_benefit: bool = False


@dataclass
class StopEvaluation:
    decision: StopDecision
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"decision": self.decision.value, "reasons": self.reasons}


def evaluate(state: DiscoveryState) -> StopEvaluation:
    reasons: list[str] = []

    if state.risk_exceeds_benefit:
        return StopEvaluation(StopDecision.ESCALATE_TO_HUMAN, ["risk exceeds expected benefit"])
    if state.data_missing:
        return StopEvaluation(StopDecision.PAUSE, ["required data missing"])
    if state.budget_spent >= state.budget_total:
        reasons.append("compute/monetary budget exhausted")
        return StopEvaluation(StopDecision.STOP, reasons)
    if state.rounds >= state.max_rounds:
        return StopEvaluation(StopDecision.STOP, ["max rounds reached"])

    # A single clearly-dominant hypothesis: stop when all but one are dominated.
    if state.total_hypotheses > 1 and state.dominated_hypotheses >= state.total_hypotheses - 1:
        return StopEvaluation(StopDecision.STOP, ["one hypothesis clearly dominates"])

    if not state.has_discriminating_experiment:
        return StopEvaluation(StopDecision.ESCALATE_TO_HUMAN,
                              ["no discriminating experiment available"])
    if state.inconclusive_streak >= state.max_inconclusive:
        return StopEvaluation(StopDecision.REFINE,
                              [f"{state.inconclusive_streak} inconclusive rounds; refine design"])
    if state.high_prior_sensitivity:
        return StopEvaluation(StopDecision.REFINE, ["results highly sensitive to priors"])
    if state.last_improvement < state.min_improvement:
        return StopEvaluation(StopDecision.STOP,
                              [f"improvement {state.last_improvement:.4f} < "
                               f"{state.min_improvement} threshold"])

    return StopEvaluation(StopDecision.CONTINUE, ["progress within budget; keep going"])
