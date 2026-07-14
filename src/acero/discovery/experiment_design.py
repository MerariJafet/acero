"""Experiment proposals and discriminating-experiment logic (Sprint 6.1/6.2).

An experiment is only worth running if it can DISTINGUISH between competing
hypotheses. We build an Experiment × Hypothesis × Expected-Outcome matrix and
reject proposals where every hypothesis predicts the same outcome (non-discriminating).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..core.clock import now_iso
from ..core.ids import new_id


class ExperimentProposal(BaseModel):
    id: str = Field(default_factory=lambda: new_id("exp"))
    project_id: str
    research_question: str
    hypotheses_tested: list[str] = Field(min_length=1)
    independent_variables: list[str] = Field(default_factory=list)
    dependent_variables: list[str] = Field(default_factory=list)
    controlled_variables: list[str] = Field(default_factory=list)
    parameter_space: dict[str, Any] = Field(default_factory=dict)
    data_requirements: list[str] = Field(default_factory=list)
    simulation_requirements: dict[str, Any] = Field(default_factory=dict)
    baseline: str = ""
    positive_control: str = ""
    negative_control: str = ""
    metrics: list[str] = Field(default_factory=list)
    preregistered_predictions: dict[str, str] = Field(default_factory=dict)  # hyp_id -> expected
    falsification_rules: list[str] = Field(default_factory=list)
    stopping_rules: list[str] = Field(default_factory=list)
    compute_budget: dict[str, Any] = Field(default_factory=dict)
    expected_information_gain: float | None = None
    expected_learning_value: float = 0.5
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    divergence_region: str = ""
    created_at: str = Field(default_factory=now_iso)
    preregistered: bool = False

    @field_validator("hypotheses_tested")
    @classmethod
    def _needs_two(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("a discriminating experiment must test >=2 hypotheses")
        return v


class DiscriminationMatrix(BaseModel):
    experiment_id: str
    # hypothesis_id -> expected outcome label in the probe region
    expected_outcomes: dict[str, str]

    @property
    def distinct_outcomes(self) -> set[str]:
        return set(self.expected_outcomes.values())

    @property
    def is_discriminating(self) -> bool:
        # At least two hypotheses must predict DIFFERENT outcomes.
        return len(self.distinct_outcomes) >= 2

    def non_distinguished_groups(self) -> list[list[str]]:
        groups: dict[str, list[str]] = {}
        for hid, outcome in self.expected_outcomes.items():
            groups.setdefault(outcome, []).append(hid)
        return [g for g in groups.values() if len(g) > 1]


def build_matrix(proposal: ExperimentProposal) -> DiscriminationMatrix:
    return DiscriminationMatrix(
        experiment_id=proposal.id,
        expected_outcomes=dict(proposal.preregistered_predictions),
    )


class NonDiscriminatingError(ValueError):
    """Raised when a proposed experiment cannot distinguish the hypotheses."""


def require_discriminating(proposal: ExperimentProposal) -> DiscriminationMatrix:
    matrix = build_matrix(proposal)
    if not proposal.preregistered_predictions:
        raise NonDiscriminatingError("No preregistered expected outcomes per hypothesis.")
    if not matrix.is_discriminating:
        raise NonDiscriminatingError(
            "All hypotheses predict the same outcome; experiment is not discriminating. "
            f"Outcomes: {matrix.expected_outcomes}"
        )
    return matrix
