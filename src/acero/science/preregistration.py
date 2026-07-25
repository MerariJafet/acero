"""Pre-registration and the two-regime separation (DISCOVERY vs CONFIRMATION).

The reviewer's most urgent gap: once ACERO has SEEN the data — explored anomalies,
repaired code, tweaked the analysis — those same data can no longer be an impartial
test of the hypothesis they generated. So we split the world in two:

  Régimen A (DISCOVERY): explore freely. Output = a *candidate* hypothesis.
  Régimen B (CONFIRMATION): BEFORE touching confirmatory data, freeze the whole plan
  (hypothesis, primary variable, population, criteria, transforms, model, primary test,
  multiplicity correction, minimum effect, decision rule, sensitivity, failure
  conditions). The plan gets a ProtocolHash. Only THEN may the held-out / new data be
  unblinded — and any change afterwards is a logged DEVIATION, not a silent edit.

The hash is computed over the SCIENTIFIC content only (never the timestamp), so it is
reproducible: the same frozen plan always yields the same hash, and any change to a
pre-registered field changes the hash — making post-hoc edits detectable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from ..core.clock import now_iso


class Regime(str, Enum):
    """Which scientific regime a result was produced under."""
    DISCOVERY = "discovery"        # saw the data first → exploratory by construction
    CONFIRMATION = "confirmation"  # frozen plan on data not yet seen


# the fields a confirmatory protocol MUST pin down before unblinding (reviewer's list)
REQUIRED_PLAN_FIELDS = (
    "hypothesis", "primary_variable", "population", "inclusion_criteria",
    "exclusion_criteria", "variable_transform", "statistical_model", "primary_test",
    "multiplicity_correction", "min_effect_size", "decision_rule", "failure_conditions",
)


@dataclass(frozen=True)
class FrozenAnalysisPlan:
    """An immutable, pre-registered confirmatory analysis plan.

    Every field is fixed BEFORE the confirmatory data is revealed. `content_dict()`
    excludes bookkeeping (author/timestamp) so the hash depends only on the science.
    """
    hypothesis: str
    primary_variable: str
    population: str
    inclusion_criteria: str
    exclusion_criteria: str
    variable_transform: str
    statistical_model: str
    primary_test: str
    multiplicity_correction: str
    min_effect_size: float
    decision_rule: str
    failure_conditions: str
    # optional but recommended
    sensitivity_analyses: tuple[str, ...] = ()
    covariates: tuple[str, ...] = ()
    # bookkeeping (NOT hashed)
    author: str = "acero"
    created_at: str = ""
    evidence_known_at_formulation: str = ""

    def content_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("author", "created_at", "evidence_known_at_formulation"):
            d.pop(k, None)
        return d

    def missing_fields(self) -> list[str]:
        """Required fields left blank/zero — a plan is not freezable until empty."""
        out = []
        for f_ in REQUIRED_PLAN_FIELDS:
            v = getattr(self, f_)
            if isinstance(v, str) and not v.strip():
                out.append(f_)
            elif isinstance(v, (int, float)) and f_ == "min_effect_size" and v == 0:
                out.append(f_)
        return out


def protocol_hash(plan: FrozenAnalysisPlan) -> str:
    """Deterministic SHA-256 over the plan's SCIENTIFIC content (sorted, canonical)."""
    blob = json.dumps(plan.content_dict(), sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Preregistration:
    """A frozen plan bound to its hash and the moment it was sealed."""
    plan: FrozenAnalysisPlan
    hash: str
    frozen_at: str


@dataclass(frozen=True)
class UnblindingEvent:
    """Records that confirmatory data was revealed AGAINST a specific frozen protocol.

    It cannot exist without a protocol hash — that is the whole point: you commit the
    analysis before you look. `dataset_ref` identifies the held-out/new evidence.
    """
    protocol_hash: str
    dataset_ref: str
    at: str
    by: str = "acero"


@dataclass
class Deviation:
    field_changed: str
    from_value: str
    to_value: str
    reason: str
    at: str


class FreezeError(RuntimeError):
    """Raised when a plan cannot be frozen (missing required fields)."""


class ProtocolRegistry:
    """Immutable store of pre-registered protocols + their unblinding/deviation history.

    Freezing is idempotent (same content → same hash → same record). A protocol can
    never be mutated after freezing; changes are recorded as append-only DEVIATIONS,
    which is exactly the audit trail a reviewer needs to judge exploratory drift.
    """

    def __init__(self) -> None:
        self._protocols: dict[str, Preregistration] = {}
        self._unblindings: dict[str, list[UnblindingEvent]] = {}
        self._deviations: dict[str, list[Deviation]] = {}

    def freeze(self, plan: FrozenAnalysisPlan) -> Preregistration:
        missing = plan.missing_fields()
        if missing:
            raise FreezeError(f"no se puede congelar: faltan campos {missing}")
        h = protocol_hash(plan)
        if h not in self._protocols:            # idempotent
            frozen_plan = plan if plan.created_at else _stamp(plan)
            self._protocols[h] = Preregistration(frozen_plan, h, now_iso())
            self._unblindings[h] = []
            self._deviations[h] = []
        return self._protocols[h]

    def get(self, protocol_hash_: str) -> Preregistration | None:
        return self._protocols.get(protocol_hash_)

    def is_registered(self, protocol_hash_: str) -> bool:
        return protocol_hash_ in self._protocols

    def can_unblind(self, protocol_hash_: str) -> bool:
        """Confirmatory data may be revealed ONLY against a registered frozen plan."""
        return self.is_registered(protocol_hash_)

    def unblind(self, protocol_hash_: str, dataset_ref: str,
                by: str = "acero") -> UnblindingEvent:
        if not self.can_unblind(protocol_hash_):
            raise PermissionError(
                "prohibido revelar datos confirmatorios sin un protocolo congelado")
        ev = UnblindingEvent(protocol_hash_, dataset_ref, now_iso(), by)
        self._unblindings[protocol_hash_].append(ev)
        return ev

    def record_deviation(self, protocol_hash_: str, field_changed: str,
                         from_value: str, to_value: str, reason: str) -> Deviation:
        if not self.is_registered(protocol_hash_):
            raise KeyError("protocolo no registrado")
        d = Deviation(field_changed, from_value, to_value, reason, now_iso())
        self._deviations[protocol_hash_].append(d)
        return d

    def unblindings(self, protocol_hash_: str) -> list[UnblindingEvent]:
        return list(self._unblindings.get(protocol_hash_, []))

    def deviations(self, protocol_hash_: str) -> list[Deviation]:
        return list(self._deviations.get(protocol_hash_, []))

    def classify(self, protocol_hash_: str | None) -> Regime:
        """A result is CONFIRMATION only if it was unblinded against a frozen plan."""
        if protocol_hash_ and self.unblindings(protocol_hash_):
            return Regime.CONFIRMATION
        return Regime.DISCOVERY


def _stamp(plan: FrozenAnalysisPlan) -> FrozenAnalysisPlan:
    from dataclasses import replace
    return replace(plan, created_at=now_iso())
