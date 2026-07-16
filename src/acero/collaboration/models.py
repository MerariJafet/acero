"""Collaboration data models (Sprint 19)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class ReviewerRole(str, Enum):
    DOMAIN_EXPERT = "DOMAIN_EXPERT"
    STATISTICIAN = "STATISTICIAN"
    METHODS_REVIEWER = "METHODS_REVIEWER"
    REPRODUCIBILITY_REVIEWER = "REPRODUCIBILITY_REVIEWER"
    DATA_EXPERT = "DATA_EXPERT"
    SECURITY_REVIEWER = "SECURITY_REVIEWER"
    ETHICS_REVIEWER = "ETHICS_REVIEWER"
    SKEPTICAL_GENERALIST = "SKEPTICAL_GENERALIST"


class WorkspaceStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    CLOSED = "CLOSED"


class CollaborationWorkspace(BaseModel):
    workspace_id: str = Field(default_factory=lambda: new_id("wsp"))
    project_id: str
    purpose: str = ""
    requested_expertise: list[ReviewerRole] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    review_questions: list[str] = Field(default_factory=list)
    confidentiality: str = "local_only"
    license: str = "unspecified"
    version: str = "2.0.0-rc2"
    status: WorkspaceStatus = WorkspaceStatus.DRAFT
    created_at: str = Field(default_factory=now_iso)


class ExternalReview(BaseModel):
    review_id: str = Field(default_factory=lambda: new_id("rev"))
    reviewer_role: ReviewerRole
    reviewed_version: str                       # commit or version the review targets
    reviewed_bundle_hash: str = ""              # binds the review to exact content
    overall_assessment: str = ""
    major_concerns: list[str] = Field(default_factory=list)
    minor_concerns: list[str] = Field(default_factory=list)
    claim_comments: list[dict] = Field(default_factory=list)     # {claim, comment}
    method_comments: list[str] = Field(default_factory=list)
    reproduction_result: str = "not_attempted"  # reproduced|failed|not_attempted
    requested_changes: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    imported_at: str = Field(default_factory=now_iso)
    trusted: bool = False                        # NEVER auto-trusted


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED_WITH_REASON = "REJECTED_WITH_REASON"
    REQUIRES_EXTERNAL_VALIDATION = "REQUIRES_EXTERNAL_VALIDATION"


class ReviewIssue(BaseModel):
    issue_id: str = Field(default_factory=lambda: new_id("iss"))
    review_id: str
    severity: str = "medium"                    # critical|high|medium|low
    category: str = "methodological"
    artifact: str = ""
    claim: str = ""
    description: str = ""
    remediation: str = ""
    owner: str = "human"
    status: IssueStatus = IssueStatus.OPEN
    evidence: list[str] = Field(default_factory=list)
    validation: str = ""


class ExternalValidationPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: new_id("evp"))
    claim: str
    required_expertise: list[ReviewerRole] = Field(default_factory=list)
    required_facility: str = ""
    required_data: str = ""
    required_experiment: str = ""
    cost_range: str = "unknown"
    duration_range: str = "unknown"
    safety_requirements: list[str] = Field(default_factory=list)
    collaboration_type: str = "external_review"
    blockers: list[str] = Field(default_factory=list)


# CRediT roles (a preliminary contribution matrix). AI is NEVER an author.
CREDIT_ROLES = (
    "conceptualization", "methodology", "software", "validation", "investigation",
    "data_curation", "writing", "visualization", "supervision",
)


class ContributionMatrix(BaseModel):
    human_author: str
    roles: dict[str, bool] = Field(default_factory=dict)     # credit_role -> contributed
    ai_assistance: list[str] = Field(default_factory=list)   # recorded SEPARATELY, not authorship

    def ai_listed_as_author(self) -> bool:
        return False                                # by construction — never
