"""HypothesisCandidate — the rich hypothesis object of the Discovery Engine (Sprint 5.1/5.4).

A candidate is more detailed than the ledger's Hypothesis entity: it carries the
mechanism, assumptions, predicted observations, falsification conditions, required
variables/data/tools, estimated compute, rationale, sources, novelty notes, risks,
and full generation provenance (prompt version, provider, model, params, tokens).

Rule: sources are recorded as *claimed* by the generator and must be verified
before use; a candidate never turns a Codex-claimed citation into evidence.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..core.clock import now_iso


class HypothesisType(str, Enum):
    DESCRIPTIVE = "DESCRIPTIVE"
    PREDICTIVE = "PREDICTIVE"
    MECHANISTIC = "MECHANISTIC"
    CAUSAL = "CAUSAL"
    MATHEMATICAL = "MATHEMATICAL"
    COMPUTATIONAL = "COMPUTATIONAL"
    ANALOGICAL = "ANALOGICAL"
    NULL = "NULL"
    BASELINE = "BASELINE"
    BOUNDARY_CASE = "BOUNDARY_CASE"


class CandidateStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"       # advanced to experiment design
    REJECTED = "REJECTED"       # kept in the registry, never deleted
    DUPLICATE = "DUPLICATE"
    WEAKENED = "WEAKENED"
    REFUTED = "REFUTED"


class GenerationProvenance(BaseModel):
    generator: str = "unknown"      # 'mock' | 'codex' | 'human'
    provider: str = "unknown"
    model: str = "unknown"
    prompt_version: str = "v1"
    params: dict[str, Any] = Field(default_factory=dict)
    token_usage: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)


class HypothesisCandidate(BaseModel):
    id: str
    research_question_id: str
    project_id: str
    title: str
    statement: str
    hypothesis_type: HypothesisType = HypothesisType.PREDICTIVE
    mechanism: str = ""
    assumptions: list[str] = Field(default_factory=list)
    predicted_observations: list[str] = Field(default_factory=list)
    falsification_conditions: list[str] = Field(default_factory=list)
    required_variables: list[str] = Field(default_factory=list)
    required_data: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    estimated_compute: dict[str, Any] = Field(default_factory=dict)
    scientific_rationale: str = ""
    # Sources are CLAIMED by the generator; verification happens separately.
    supporting_sources: list[str] = Field(default_factory=list)
    contradictory_sources: list[str] = Field(default_factory=list)
    sources_verified: bool = False
    novelty_notes: str = ""
    risks: list[str] = Field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED
    rejection: dict[str, Any] | None = None  # reason/evaluator/evidence/scores/reconsider_if
    scores: dict[str, float] = Field(default_factory=dict)
    generation: GenerationProvenance = Field(default_factory=GenerationProvenance)
    created_at: str = Field(default_factory=now_iso)

    @field_validator("title", "statement")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("candidate title/statement must be non-empty")
        return v

    def mechanism_signature(self) -> str:
        """A normalised token signature of the mechanism, for structural diversity."""
        import re

        text = (self.mechanism or self.statement).lower()
        toks = re.findall(r"[a-z0-9]+", text)
        stop = {"the", "a", "of", "to", "and", "in", "is", "model", "la", "el", "de", "y"}
        return " ".join(sorted({t for t in toks if t not in stop and len(t) > 2}))
