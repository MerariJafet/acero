"""First Principles Engine data models (Sprint 8.7)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ...core.clock import now_iso
from ...core.ids import new_id


class ModelType(str, Enum):
    PREDICTIVE = "PREDICTIVE"
    MECHANISTIC = "MECHANISTIC"
    CAUSAL = "CAUSAL"
    PHENOMENOLOGICAL = "PHENOMENOLOGICAL"
    EFFECTIVE = "EFFECTIVE"
    FUNDAMENTAL = "FUNDAMENTAL"


class FirstPrinciplesProblem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("fpp"))
    project_id: str
    phenomenon: str
    observations: list[str] = Field(default_factory=list)
    # variable -> dimension name (cognitive.dimensions.NAMED)
    variables: dict[str, str] = Field(default_factory=dict)
    known_constraints: list[str] = Field(default_factory=list)
    candidate_symmetries: list[str] = Field(default_factory=list)
    conservation_rules: list[str] = Field(default_factory=list)
    boundary_conditions: list[str] = Field(default_factory=list)
    limiting_cases: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    forbidden_assumptions: list[str] = Field(default_factory=list)
    target_quantity: str = ""
    desired_explanation: str = ""
    created_at: str = Field(default_factory=now_iso)


class DerivationStep(BaseModel):
    index: int
    description: str
    expression: str = ""            # SymPy-parseable, when applicable
    justification: str = ""
    check_kind: str = "none"        # symbolic | dimensional | numerical | none
    verified: bool = False
    detail: str = ""
    proposed_by: str = "rules"      # rules | codex | human


class ScientificDerivation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("der"))
    project_id: str
    target: str
    premises: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    definitions: dict[str, str] = Field(default_factory=dict)
    steps: list[DerivationStep] = Field(default_factory=list)
    conclusion: str = ""
    limiting_cases: list[str] = Field(default_factory=list)
    counterexamples: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    generator: str = "rules"
    created_at: str = Field(default_factory=now_iso)

    @property
    def unresolved_steps(self) -> list[int]:
        return [s.index for s in self.steps if s.check_kind != "none" and not s.verified]

    @property
    def all_verified(self) -> bool:
        checkable = [s for s in self.steps if s.check_kind != "none"]
        return bool(checkable) and all(s.verified for s in checkable)


class ModelCandidate(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mc"))
    expression: str                 # e.g. "a*t + b", "K/(1+A*exp(-r*t))"
    n_parameters: int
    n_terms: int
    model_type: ModelType = ModelType.PHENOMENOLOGICAL
    conserves: list[str] = Field(default_factory=list)
    dissipates: list[str] = Field(default_factory=list)
    dimensionally_valid: bool = True
    satisfies_constraints: bool = True
    fit_rmse: float | None = None
    extrapolation_rmse: float | None = None
    notes: str = ""
