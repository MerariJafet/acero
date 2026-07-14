"""Analogy models (Sprint 8.6).

An analogy is a structural correspondence between two systems — NOT verbal
similarity. We represent each system by its variables (with dimensions), the roles
its terms play in a governing equation, invariants, and symmetries; the analogy maps
these across domains and records what structure is preserved vs broken.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ...core.clock import now_iso
from ...core.ids import new_id


class AnalogyType(str, Enum):
    SURFACE = "SURFACE"
    FUNCTIONAL = "FUNCTIONAL"
    STRUCTURAL = "STRUCTURAL"
    MATHEMATICAL = "MATHEMATICAL"
    DYNAMICAL = "DYNAMICAL"
    CAUSAL = "CAUSAL"
    MECHANISTIC = "MECHANISTIC"
    SYMMETRY_BASED = "SYMMETRY_BASED"
    INFORMATIONAL = "INFORMATIONAL"
    LIMITING_CASE = "LIMITING_CASE"


class AnalogyStatus(str, Enum):
    PROPOSED = "PROPOSED"
    STRUCTURALLY_SUPPORTED = "STRUCTURALLY_SUPPORTED"
    PARTIALLY_VALID = "PARTIALLY_VALID"
    VALID_IN_REGIME = "VALID_IN_REGIME"
    BROKEN = "BROKEN"
    MISLEADING = "MISLEADING"
    REJECTED = "REJECTED"


class SystemRepresentation(BaseModel):
    """A structural description of a physical system for analogy comparison."""

    name: str
    domain: str
    # variable name -> dimension name (see cognitive.dimensions.NAMED)
    variables: dict[str, str] = Field(default_factory=dict)
    # canonical structural form of the governing equation, e.g.
    # "2nd_order_linear_ode: a*y'' + b*y' + c*y = f"
    structural_form: str = ""
    # role -> variable name; roles are domain-neutral (inertia/dissipation/restoring/…)
    term_roles: dict[str, str] = Field(default_factory=dict)
    invariants: list[str] = Field(default_factory=list)
    symmetries: list[str] = Field(default_factory=list)
    # named dimensionless groups -> formula over variables (for transfer/limits)
    dimensionless_groups: dict[str, str] = Field(default_factory=dict)
    notes: str = ""


class AnalogyScores(BaseModel):
    structural_similarity: float = 0.0
    mathematical_similarity: float = 0.0
    causal_similarity: float = 0.0
    invariant_preservation: float = 0.0
    boundary_compatibility: float = 0.0
    predictive_transferability: float = 0.0
    surface_similarity: float = 0.0     # weighted LOW in any aggregate
    failure_risk: float = 0.0

    def deep_score(self) -> float:
        """A HEURISTIC summary (uncalibrated) weighting deep structure heavily and
        surface similarity low. Rounded to 2 dp to avoid implying false precision."""
        raw = (0.35 * self.structural_similarity
               + 0.25 * self.mathematical_similarity
               + 0.15 * self.invariant_preservation
               + 0.15 * self.predictive_transferability
               + 0.05 * self.boundary_compatibility
               + 0.05 * self.surface_similarity
               - 0.2 * self.failure_risk)
        return round(max(0.0, raw), 2)


class ValidationResult(BaseModel):
    test: str
    passed: bool
    detail: str = ""


class ScientificAnalogy(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ana"))
    project_id: str
    source_system: str
    target_system: str
    source_domain: str
    target_domain: str
    analogy_type: AnalogyType = AnalogyType.STRUCTURAL
    entity_mapping: dict[str, str] = Field(default_factory=dict)
    relation_mapping: dict[str, str] = Field(default_factory=dict)
    equation_mapping: dict[str, str] = Field(default_factory=dict)
    invariant_mapping: dict[str, str] = Field(default_factory=dict)
    preserved_structure: list[str] = Field(default_factory=list)
    broken_structure: list[str] = Field(default_factory=list)
    transfer_predictions: list[str] = Field(default_factory=list)
    failure_conditions: list[str] = Field(default_factory=list)
    scores: AnalogyScores = Field(default_factory=AnalogyScores)
    validations: list[ValidationResult] = Field(default_factory=list)
    status: AnalogyStatus = AnalogyStatus.PROPOSED
    generator: str = "rules"
    provenance: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)
