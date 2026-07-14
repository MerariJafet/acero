"""Structured representation of a scientific concept (Sprint 8.5).

A concept is NOT an LLM paragraph. Its meaning is stored structurally: multiple
definition kinds, applicability regimes, dependencies, invariants/symmetries, a
mathematical representation, and a versioned transformation history.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ...core.clock import now_iso
from ...core.ids import new_id


class ConceptType(str, Enum):
    ENTITY = "ENTITY"
    PROPERTY = "PROPERTY"
    PROCESS = "PROCESS"
    MECHANISM = "MECHANISM"
    RELATION = "RELATION"
    LAW = "LAW"
    PRINCIPLE = "PRINCIPLE"
    CONSTRAINT = "CONSTRAINT"
    SYMMETRY = "SYMMETRY"
    INVARIANT = "INVARIANT"
    STATE = "STATE"
    TRANSITION = "TRANSITION"
    FIELD = "FIELD"
    FORCE = "FORCE"
    INFORMATION = "INFORMATION"
    ENERGY = "ENERGY"
    SYSTEM = "SYSTEM"
    EMERGENCE = "EMERGENCE"
    CAUSAL_STRUCTURE = "CAUSAL_STRUCTURE"
    MATHEMATICAL_STRUCTURE = "MATHEMATICAL_STRUCTURE"


class DefinitionSet(BaseModel):
    """A concept can be defined several ways; a paragraph is not enough."""

    lexical: str = ""
    operational: str = ""
    mathematical: str = ""     # e.g. "T = T_env + (T0-T_env) e^{-k t}"
    causal: str = ""
    behavioral: str = ""
    by_constraints: str = ""


class ApplicabilityRegime(BaseModel):
    label: str = ""
    domain: str = "general"
    spatial_scale: str = ""
    temporal_scale: str = ""
    energy_scale: str = ""
    parameter_ranges: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    valid_conditions: list[str] = Field(default_factory=list)
    invalid_conditions: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class ConceptualTransformation(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ctf"))
    previous_model: str
    new_model: str
    preserved_predictions: list[str] = Field(default_factory=list)
    changed_assumptions: list[str] = Field(default_factory=list)
    new_explanatory_power: str = ""
    unresolved_problems: list[str] = Field(default_factory=list)
    triggering_evidence: list[str] = Field(default_factory=list)
    historical_context: str = ""
    compatibility: str = "partial"   # backward_compatible | partial | incompatible
    replacement_scope: str = ""
    # NOT automatically "progress" — must be evaluated.
    assessed_as_progress: bool | None = None
    created_at: str = Field(default_factory=now_iso)


class ScientificConcept(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cpt"))
    project_id: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    concept_type: ConceptType = ConceptType.PROPERTY
    domain: str = "general"
    subdomains: list[str] = Field(default_factory=list)
    abstraction_level: int = 1     # 1 concrete … higher = more abstract
    definitions: DefinitionSet = Field(default_factory=DefinitionSet)
    mathematical_representation: str = ""
    units: str = ""
    dimensions: dict[str, str] = Field(default_factory=dict)  # base-dim -> exponent
    variables: list[str] = Field(default_factory=list)
    parameters: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    symmetries: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    counterexamples: list[str] = Field(default_factory=list)
    applicable_regimes: list[ApplicabilityRegime] = Field(default_factory=list)
    invalid_regimes: list[ApplicabilityRegime] = Field(default_factory=list)
    boundary_conditions: list[str] = Field(default_factory=list)
    historical_versions: list[ConceptualTransformation] = Field(default_factory=list)
    supporting_sources: list[str] = Field(default_factory=list)  # claimed; unverified
    sources_verified: bool = False
    generator: str = "human"       # human | codex | rules
    created_at: str = Field(default_factory=now_iso)

    @field_validator("canonical_name")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("canonical_name must be non-empty")
        return v
