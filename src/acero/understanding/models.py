"""Data models for the Human Understanding Engine (Sprint 9).

Every enum here is load-bearing: a KnowledgeStatus transition requires evidence, an
EvidenceType names a *different* performance task, and an ExplanationLevel is a separate
artifact. None of them is decorative.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class KnowledgeStatus(str, Enum):
    """Where a learner stands on one concept. Transitions require evidence."""

    UNKNOWN = "UNKNOWN"
    EXPOSED = "EXPOSED"
    RECOGNIZED = "RECOGNIZED"
    PARTIALLY_UNDERSTOOD = "PARTIALLY_UNDERSTOOD"
    PROCEDURALLY_COMPETENT = "PROCEDURALLY_COMPETENT"
    CONCEPTUALLY_UNDERSTOOD = "CONCEPTUALLY_UNDERSTOOD"
    TRANSFER_CAPABLE = "TRANSFER_CAPABLE"
    MASTERED = "MASTERED"
    MISCONCEIVED = "MISCONCEIVED"
    DECAYED = "DECAYED"


class EvidenceType(str, Enum):
    """Understanding is measured through DIFFERENT tasks — never one kind alone."""

    EXPLAIN_OWN_WORDS = "explain_own_words"
    PREDICT_BEFORE_RESULT = "predict_before_result"
    SOLVE_SIMILAR = "solve_similar"
    DETECT_ERROR = "detect_error"
    IDENTIFY_ASSUMPTION = "identify_assumption"
    INTERPRET_GRAPH = "interpret_graph"
    MODIFY_CODE = "modify_code"
    DERIVE_RESULT = "derive_result"
    COMPARE_MODELS = "compare_models"
    TRANSFER = "transfer"
    PROPOSE_FALSIFICATION = "propose_falsification"
    STATE_LIMITS = "state_limits"


class ExplanationLevel(str, Enum):
    INTUITION = "intuition"
    CONCEPTUAL = "conceptual"
    MATHEMATICAL = "mathematical"
    COMPUTATIONAL = "computational"
    FRONTIER = "frontier"


class ExplainMode(str, Enum):
    EXPLAIN_INTUITION = "EXPLAIN_INTUITION"
    EXPLAIN_MATHEMATICS = "EXPLAIN_MATHEMATICS"
    EXPLAIN_CODE = "EXPLAIN_CODE"
    EXPLAIN_EVIDENCE = "EXPLAIN_EVIDENCE"
    EXPLAIN_ASSUMPTIONS = "EXPLAIN_ASSUMPTIONS"
    EXPLAIN_FAILURE = "EXPLAIN_FAILURE"
    EXPLAIN_UNCERTAINTY = "EXPLAIN_UNCERTAINTY"
    EXPLAIN_ABSTENTION = "EXPLAIN_ABSTENTION"
    EXPLAIN_NEXT_EXPERIMENT = "EXPLAIN_NEXT_EXPERIMENT"


class Criticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKING = "blocking"


class LearnerProfile(BaseModel):
    learner_id: str = Field(default_factory=lambda: new_id("lrn"))
    preferred_name: str = "researcher"
    research_domains: list[str] = Field(default_factory=list)
    mathematical_background: str = "unknown"
    programming_background: str = "unknown"
    scientific_background: str = "unknown"
    preferred_explanation_style: str = "balanced"     # intuition|formal|balanced
    preferred_depth: str = "adaptive"
    learning_goals: list[str] = Field(default_factory=list)
    active_research_projects: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class KnowledgeState(BaseModel):
    concept_id: str
    learner_id: str
    familiarity: float = 0.0                 # 0..1 exposure
    conceptual_understanding: float = 0.0
    procedural_ability: float = 0.0
    mathematical_ability: float = 0.0
    transfer_ability: float = 0.0
    confidence_self_reported: float = 0.0
    confidence_observed: float = 0.0
    misconceptions: list[str] = Field(default_factory=list)   # misconception ids
    evidence: list[str] = Field(default_factory=list)         # evidence ids
    last_assessed: str | None = None
    next_review: str | None = None
    status: KnowledgeStatus = KnowledgeStatus.UNKNOWN


class UnderstandingEvidence(BaseModel):
    id: str = Field(default_factory=lambda: new_id("uev"))
    learner_id: str
    concept_id: str
    evidence_type: EvidenceType
    task: str
    response: str
    expected_elements: list[str] = Field(default_factory=list)
    score: float = 0.0                        # 0..1 (may be partial credit)
    confidence: float = 0.0                   # learner self-reported for this task
    grader: str = "rubric"                    # rubric|human|codex-advisory
    rubric_version: str = "v1"
    research_context: str | None = None       # project/artifact id
    timestamp: str = Field(default_factory=now_iso)


class Misconception(BaseModel):
    id: str = Field(default_factory=lambda: new_id("misc"))
    learner_id: str
    concept: str
    statement: str
    detected_from: str                        # evidence id or artifact
    severity: Criticality = Criticality.MEDIUM
    evidence: list[str] = Field(default_factory=list)
    corrective_activity: str = ""
    resolved: bool = False
    resolution_evidence: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)


class ResearchLearningRequirement(BaseModel):
    id: str = Field(default_factory=lambda: new_id("rlr"))
    research_project_id: str
    concept: str
    reason_required: str
    criticality: Criticality = Criticality.MEDIUM
    prerequisite_concepts: list[str] = Field(default_factory=list)
    related_equations: list[str] = Field(default_factory=list)
    related_code: list[str] = Field(default_factory=list)
    related_assumptions: list[str] = Field(default_factory=list)
    required_mastery_level: KnowledgeStatus = KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD
    blocking: bool = False


class ExplanationArtifact(BaseModel):
    id: str = Field(default_factory=lambda: new_id("exp"))
    subject: str
    level: ExplanationLevel
    prerequisites: list[str] = Field(default_factory=list)
    content: str = ""
    equations: list[str] = Field(default_factory=list)
    code_references: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)     # author, source, tokens


class HumanPrediction(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pred"))
    learner_id: str
    research_project_id: str
    experiment_id: str
    predicted_outcome: str
    rationale: str = ""
    confidence: float = 0.5
    timestamp: str = Field(default_factory=now_iso)
    revealed_result: str | None = None        # None until the result is revealed
    comparison: str | None = None             # correct|partial|incorrect
    reflection: str | None = None
    locked: bool = False                      # True once a result is revealed


class LearningExercise(BaseModel):
    id: str = Field(default_factory=lambda: new_id("exr"))
    concept: str
    research_context: str
    task: str
    difficulty: str = "medium"
    prerequisites: list[str] = Field(default_factory=list)
    expected_reasoning: list[str] = Field(default_factory=list)
    rubric: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    solution: str = ""
    common_errors: list[str] = Field(default_factory=list)
    transfer_task: str = ""


class ComprehensionStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_SUPPORT = "PASS_WITH_SUPPORT"
    BLOCKED_FOR_LEARNING = "BLOCKED_FOR_LEARNING"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"


class ComprehensionGateResult(BaseModel):
    decision: str
    required_concepts: list[str] = Field(default_factory=list)
    required_level: KnowledgeStatus = KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD
    assessments: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    status: ComprehensionStatus = ComprehensionStatus.PASS
    blockers: list[str] = Field(default_factory=list)
    human_override: bool = False
    override_reason: str | None = None
    timestamp: str = Field(default_factory=now_iso)
