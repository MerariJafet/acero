"""Canonical schema for the Scientific Knowledge Mesh (Phase 1)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class ObjectType(str, Enum):
    """Epistemic type of a knowledge unit. An ACERO inference is NEVER an observation."""
    OBSERVATION = "OBSERVATION"
    EXPERIMENTAL_DATA = "EXPERIMENTAL_DATA"
    SIMULATION = "SIMULATION"
    DERIVED_DATA = "DERIVED_DATA"
    PEER_REVIEWED_ARTICLE = "PEER_REVIEWED_ARTICLE"
    PREPRINT = "PREPRINT"
    REVIEW = "REVIEW"
    META_ANALYSIS = "META_ANALYSIS"
    DATASET = "DATASET"
    SOFTWARE = "SOFTWARE"
    PROTOCOL = "PROTOCOL"
    STANDARD = "STANDARD"
    THEORY = "THEORY"
    MODEL = "MODEL"
    HYPOTHESIS = "HYPOTHESIS"
    NEGATIVE_RESULT = "NEGATIVE_RESULT"
    RETRACTED_WORK = "RETRACTED_WORK"
    CORRECTED_WORK = "CORRECTED_WORK"
    ACERO_INFERENCE = "ACERO_INFERENCE"
    ACERO_HYPOTHESIS = "ACERO_HYPOTHESIS"
    ACERO_EXPERIMENT = "ACERO_EXPERIMENT"
    UNKNOWN = "UNKNOWN"


# object types that are ACERO/AI-generated and must never be treated as observed evidence
ACERO_GENERATED = {ObjectType.ACERO_INFERENCE, ObjectType.ACERO_HYPOTHESIS,
                   ObjectType.ACERO_EXPERIMENT}


class AuthorityLevel(str, Enum):
    PRIMARY = "primary"
    OFFICIAL_AGGREGATOR = "official_aggregator"
    SECONDARY = "secondary"
    COMMUNITY = "community"


class HealthStatus(str, Enum):
    ACTIVE = "active"
    PARTIAL = "partial"
    DEPRECATED = "deprecated"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class ProvenanceStep(BaseModel):
    at: str = Field(default_factory=now_iso)
    agent: str
    action: str
    detail: str = ""


class SourceRecord(BaseModel):
    """A verified scientific source (Scientific Source Registry entry)."""
    source_id: str
    name: str
    canonical_domain: str
    responsible_institution: str
    scientific_domains: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    authority_level: AuthorityLevel = AuthorityLevel.SECONDARY
    documentation_url: str = ""
    api_base_url: str = ""
    health_check_url: str = ""
    authentication: str = "none"
    metadata_license: str = "unknown"
    file_license_model: str = "varies"
    commercial_use: str = "unknown"
    personal_data_risk: str = "none"
    bulk_access: str = ""
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_health_check: str | None = None
    last_http_status: int | None = None
    connector_status: str = "not_started"   # not_started|prototype|tested|production
    notes: list[str] = Field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ScientificObject(BaseModel):
    """A canonical, traceable scientific object (paper/dataset/observation/...)."""
    object_id: str = Field(default_factory=lambda: new_id("sci"))
    object_type: ObjectType
    title: str = ""
    abstract: str | None = None
    identifiers: dict[str, list[str]] = Field(default_factory=dict)  # doi/arxiv/pmid/...
    authors: list[str] = Field(default_factory=list)
    institutions: list[str] = Field(default_factory=list)
    publication_dates: dict[str, str] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    license: dict[str, Any] = Field(default_factory=dict)
    access_status: str = "unknown"           # open|metadata_only|embargoed|restricted|...
    review_status: str = "unknown"           # peer_reviewed|preprint|editorial|unknown
    integrity_status: str = "normal"         # normal|corrected|retracted|expression_of_concern
    source_id: str = ""
    canonical_url: str = ""
    files: list[dict[str, Any]] = Field(default_factory=list)
    provenance: list[ProvenanceStep] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    ingested_at: str = Field(default_factory=now_iso)

    @property
    def is_acero_generated(self) -> bool:
        return self.object_type in ACERO_GENERATED

    def add_provenance(self, agent: str, action: str, detail: str = "") -> None:
        self.provenance.append(ProvenanceStep(agent=agent, action=action, detail=detail))

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
