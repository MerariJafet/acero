"""Governing Structure Inference data models (Sprints 8.8–8.9)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class InferenceLevel(str, Enum):
    """What level did ACERO actually reach — never overstate."""

    CURVE_FITTING = "curve_fitting"
    SYSTEM_IDENTIFICATION = "system_identification"
    SYMBOLIC_REGRESSION = "symbolic_regression"
    GOVERNING_EQUATION_DISCOVERY = "governing_equation_discovery"
    CAUSAL_DISCOVERY = "causal_discovery"
    MECHANISTIC_EXPLANATION = "mechanistic_explanation"


class IdentifiabilityStatus(str, Enum):
    IDENTIFIABLE = "IDENTIFIABLE"
    PARTIALLY_IDENTIFIABLE = "PARTIALLY_IDENTIFIABLE"
    NON_IDENTIFIABLE = "NON_IDENTIFIABLE"
    DATA_INSUFFICIENT = "DATA_INSUFFICIENT"
    REGIME_DEPENDENT = "REGIME_DEPENDENT"


class StructureInferenceProblem(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sip"))
    project_id: str
    phenomenon: str
    variables_observed: list[str] = Field(default_factory=list)
    candidate_hidden_variables: list[str] = Field(default_factory=list)
    units: dict[str, str] = Field(default_factory=dict)
    dimensions: dict[str, str] = Field(default_factory=dict)  # var -> dimension name
    temporal_coordinate: str = "t"
    spatial_coordinates: list[str] = Field(default_factory=list)
    initial_conditions: dict[str, float] = Field(default_factory=dict)
    boundary_conditions: list[str] = Field(default_factory=list)
    known_constraints: list[str] = Field(default_factory=list)
    candidate_symmetries: list[str] = Field(default_factory=list)
    candidate_conservation_rules: list[str] = Field(default_factory=list)
    allowed_transformations: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    noise_model: str = "unknown"
    sampling_information: dict[str, Any] = Field(default_factory=dict)
    inference_goal: str = "recover governing ODE terms"
    created_at: str = Field(default_factory=now_iso)


class VariableRoleAssessment(BaseModel):
    variable: str
    predictive_relevance: float = 0.0
    structural_relevance: float = 0.0
    redundancy: float = 0.0
    near_constant: bool = False
    temporal_precedence: str = "unknown"
    dimensional_role: str = ""
    candidate_interactions: list[str] = Field(default_factory=list)
    uncertainty: float = 0.0
    note: str = "predictive != causal"


class GoverningModelCandidate(BaseModel):
    id: str = Field(default_factory=lambda: new_id("gmc"))
    target: str                       # e.g. "dx/dt"
    expression: str                   # human-readable inferred RHS
    equation_type: str = "ODE"
    variables: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)
    coefficients: dict[str, float] = Field(default_factory=dict)
    dimensions_valid: bool = True
    assumptions: list[str] = Field(default_factory=list)
    valid_regime: str = ""
    conserved_quantities: list[str] = Field(default_factory=list)
    symmetries: list[str] = Field(default_factory=list)
    fit_metrics: dict[str, float] = Field(default_factory=dict)
    stability_metrics: dict[str, Any] = Field(default_factory=dict)
    extrapolation_metrics: dict[str, float] = Field(default_factory=dict)
    complexity: int = 0
    identifiability: IdentifiabilityStatus = IdentifiabilityStatus.IDENTIFIABLE
    unresolved_terms: list[str] = Field(default_factory=list)
    inference_level: InferenceLevel = InferenceLevel.SYSTEM_IDENTIFICATION
    imposed: list[str] = Field(default_factory=list)   # what was imposed (library/constraints)
    inferred: list[str] = Field(default_factory=list)  # what was inferred from data
    provenance: dict[str, Any] = Field(default_factory=dict)


class RegimeCandidate(BaseModel):
    range: tuple[float, float]
    governing_candidate: str = ""
    transition_evidence: float = 0.0
    confidence: float = 0.0
    alternatives: list[str] = Field(default_factory=list)
