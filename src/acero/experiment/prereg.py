"""Preregistration (Sprint 4).

Before any experiment runs, a complete preregistration must exist. This is the
technical guard against HARKing and p-hacking: predictions and success criteria
are fixed and hashed *before* seeing results.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ..core.clock import now_iso
from ..core.errors import IntegrityError
from ..core.hashing import hash_json


class Preregistration(BaseModel):
    project_id: str
    experiment_id: str
    question: str
    hypotheses: list[str] = Field(min_length=2)   # competing hypotheses required
    predictions: list[str] = Field(min_length=1)
    variables: dict = Field(default_factory=dict)
    metric: str
    baseline: str
    controls: list[str] = Field(default_factory=list)
    result_that_would_support: str
    result_that_would_weaken: str
    stopping_criterion: str
    compute_budget: dict = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    registered_at: str = Field(default_factory=now_iso)

    @field_validator("metric", "baseline", "result_that_would_support",
                     "result_that_would_weaken", "stopping_criterion")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("preregistration field must be non-empty")
        return v

    def prereg_hash(self) -> str:
        """A hash of the committed prereg, computed before results are known."""
        payload = self.model_dump(exclude={"registered_at"})
        return hash_json(payload)


def require_complete(prereg: Preregistration) -> str:
    """Validate completeness and return the prereg hash. Raises on incompleteness."""
    if len(prereg.hypotheses) < 2:
        raise IntegrityError("Preregistration requires at least two competing hypotheses.")
    if not prereg.predictions:
        raise IntegrityError("Preregistration requires at least one prediction.")
    return prereg.prereg_hash()
