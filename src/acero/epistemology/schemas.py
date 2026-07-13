"""Pydantic v2 schemas for the ACERO scientific record.

These are the validated, serialisable shapes of every scientific object. The
SQLAlchemy models (ledger/models.py) mirror these for persistence; these are the
contract used by the API, CLI, and export.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..core.clock import now_iso
from .types import EntityState, EntityType


class ConfidenceAssessment(BaseModel):
    """A calibrated confidence statement. Confidence is a claim, not a fact."""

    value: float = Field(ge=0.0, le=1.0, description="Subjective probability [0,1]")
    method: str = "human_estimate"
    uncertainty: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str = ""


class ProvenanceRef(BaseModel):
    """A pointer into the provenance chain (source doc, fragment, run, dataset)."""

    kind: str  # source_document | source_fragment | execution_run | dataset | code
    ref_id: str
    detail: str = ""


class EntityBase(BaseModel):
    """Fields common to every scientific object."""

    id: str
    type: EntityType
    project_id: str
    title: str
    description: str = ""
    author: str = "human"  # 'human' or an agent name; ACERO never claims authorship
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    version: int = 1
    state: EntityState = EntityState.DRAFT
    confidence: ConfidenceAssessment | None = None
    provenance: list[ProvenanceRef] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def _title_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must be non-empty")
        return v


class ResearchProject(BaseModel):
    id: str
    title: str
    description: str = ""
    domain: str = "general"  # physics | astronomy | genetics | chemistry | math | ...
    created_at: str = Field(default_factory=now_iso)
    principal_investigator: str = "human"
    state: EntityState = EntityState.ACTIVE


class ResearchQuestion(EntityBase):
    type: EntityType = EntityType.QUESTION


class Assumption(EntityBase):
    type: EntityType = EntityType.ASSUMPTION


class Hypothesis(EntityBase):
    type: EntityType = EntityType.HYPOTHESIS
    question_id: str
    falsifiable: bool = True
    falsification_criteria: str = ""

    @field_validator("question_id")
    @classmethod
    def _needs_question(cls, v: str) -> str:
        if not v:
            raise ValueError("a hypothesis must belong to a question (question_id required)")
        return v


class Prediction(EntityBase):
    type: EntityType = EntityType.PREDICTION
    hypothesis_id: str
    would_support: str = ""     # observation that would support the hypothesis
    would_weaken: str = ""      # observation that would weaken/refute it

    @field_validator("hypothesis_id")
    @classmethod
    def _needs_hypothesis(cls, v: str) -> str:
        if not v:
            raise ValueError("a prediction must belong to a hypothesis (hypothesis_id required)")
        return v


class ExperimentPlan(EntityBase):
    type: EntityType = EntityType.EXPERIMENT
    prediction_ids: list[str] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    metric: str = ""
    baseline: str = ""
    controls: list[str] = Field(default_factory=list)
    stopping_criterion: str = ""
    compute_budget: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    preregistered: bool = False

    @field_validator("prediction_ids")
    @classmethod
    def _tests_a_prediction(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("an experiment must test at least one prediction")
        return v


class ExecutionRun(BaseModel):
    id: str
    project_id: str
    experiment_id: str
    started_at: str = Field(default_factory=now_iso)
    finished_at: str | None = None
    environment: dict[str, Any] = Field(default_factory=dict)
    seeds: list[int] = Field(default_factory=list)
    input_hash: str = ""
    code_hash: str = ""
    output_hash: str = ""
    exit_code: int | None = None
    status: str = "created"  # created | running | ok | failed | timeout
    artifacts_dir: str = ""


class Evidence(EntityBase):
    type: EntityType = EntityType.EVIDENCE
    supports: list[str] = Field(default_factory=list)  # ids it supports
    source_fragment_id: str | None = None

    @field_validator("provenance")
    @classmethod
    def _evidence_needs_provenance(cls, v: list[ProvenanceRef]) -> list[ProvenanceRef]:
        if not v:
            raise ValueError("evidence must carry provenance (no evidence without provenance)")
        return v


class CounterEvidence(EntityBase):
    type: EntityType = EntityType.COUNTEREVIDENCE
    against: list[str] = Field(default_factory=list)
    source_fragment_id: str | None = None

    @field_validator("provenance")
    @classmethod
    def _counter_needs_provenance(cls, v: list[ProvenanceRef]) -> list[ProvenanceRef]:
        if not v:
            raise ValueError("counter-evidence must carry provenance")
        return v


class ResearchResult(EntityBase):
    type: EntityType = EntityType.RESULT
    run_id: str
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def _needs_run(cls, v: str) -> str:
        if not v:
            raise ValueError("a result must belong to an execution run (run_id required)")
        return v


class NegativeResult(EntityBase):
    type: EntityType = EntityType.NEGATIVE_RESULT
    run_id: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    # Negative results can never be silently deleted; see ledger.service.


class ScientificClaim(EntityBase):
    type: EntityType = EntityType.CLAIM
    is_speculation: bool = False
    supported_by: list[str] = Field(default_factory=list)
    contradicted_by: list[str] = Field(default_factory=list)


class OpenQuestion(EntityBase):
    type: EntityType = EntityType.OPEN_QUESTION


class DecisionRecord(BaseModel):
    id: str
    project_id: str
    title: str
    decision: str
    rationale: str = ""
    decided_by: str = "human"
    created_at: str = Field(default_factory=now_iso)
    related_ids: list[str] = Field(default_factory=list)


ENTITY_MODEL_BY_TYPE: dict[EntityType, type[BaseModel]] = {
    EntityType.QUESTION: ResearchQuestion,
    EntityType.ASSUMPTION: Assumption,
    EntityType.HYPOTHESIS: Hypothesis,
    EntityType.PREDICTION: Prediction,
    EntityType.EXPERIMENT: ExperimentPlan,
    EntityType.EVIDENCE: Evidence,
    EntityType.COUNTEREVIDENCE: CounterEvidence,
    EntityType.RESULT: ResearchResult,
    EntityType.NEGATIVE_RESULT: NegativeResult,
    EntityType.CLAIM: ScientificClaim,
    EntityType.OPEN_QUESTION: OpenQuestion,
}
