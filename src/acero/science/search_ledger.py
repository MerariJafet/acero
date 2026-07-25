"""Search Space Ledger — account for the WHOLE space ACERO explored, not one script.

The reviewer's point: the danger isn't how many p-values one script computes, it's how
many chances the *entire autonomous system* had to produce something striking — across
hypotheses, datasets, subsets, variables, transforms, models, endpoints, seeds and
exclusions. Even if no single run looks abusive, the garden of forking paths can be
enormous.

There is no universal correction for adaptive exploration. What we CAN do — and enforce
by code — is refuse to pretend the final analysis was the only analysis. This ledger
records every researcher degree of freedom, estimates the effective number of
comparisons ("exploration debt"), and classifies each result as exploratory unless it
survives a frozen confirmatory protocol on new evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from ..core.clock import now_iso
from .preregistration import Regime

if TYPE_CHECKING:
    from .preregistration import ProtocolRegistry


class Axis(str, Enum):
    """Researcher degrees of freedom. FORKING axes multiply the search space."""
    HYPOTHESIS = "hypothesis"
    DATASET = "dataset"
    COLUMN = "column"
    SUBSET = "subset"
    TRANSFORM = "transform"
    MODEL = "model"
    ENDPOINT = "endpoint"
    HYPERPARAM = "hyperparam"
    SEED = "seed"
    EXCLUSION = "exclusion"
    METRIC = "metric"            # observed outcome (not a fork, but a peek)
    REPAIR = "repair"            # code repair after an error
    DECISION_AFTER_DATA = "decision_after_data"  # THE risk flag


# axes whose distinct choices multiply the "chances to find something" (forking paths)
_FORKING = (Axis.COLUMN, Axis.SUBSET, Axis.TRANSFORM, Axis.MODEL, Axis.ENDPOINT,
            Axis.HYPERPARAM, Axis.EXCLUSION, Axis.SEED)


@dataclass
class SearchEvent:
    axis: Axis
    detail: str
    at: str
    after_seeing_data: bool = False


@dataclass
class SearchSpaceLedger:
    """Append-only log of everything explored during a mission."""
    mission_id: str = ""
    events: list[SearchEvent] = field(default_factory=list)
    _data_seen: bool = False

    # --- recording -----------------------------------------------------------
    def record(self, axis: Axis, detail: str, *, after_seeing_data: bool | None = None
               ) -> SearchEvent:
        seen = self._data_seen if after_seeing_data is None else after_seeing_data
        ev = SearchEvent(axis, detail.strip(), now_iso(), seen)
        self.events.append(ev)
        return ev

    def mark_data_seen(self) -> None:
        """Once the data has been inspected, later choices are post-hoc by default."""
        self._data_seen = True

    # convenience wrappers (read at call sites like a lab notebook)
    def hypothesis(self, d: str) -> SearchEvent: return self.record(Axis.HYPOTHESIS, d)
    def dataset(self, d: str) -> SearchEvent: return self.record(Axis.DATASET, d)
    def column(self, d: str) -> SearchEvent: return self.record(Axis.COLUMN, d)
    def subset(self, d: str) -> SearchEvent: return self.record(Axis.SUBSET, d)
    def transform(self, d: str) -> SearchEvent: return self.record(Axis.TRANSFORM, d)
    def model(self, d: str) -> SearchEvent: return self.record(Axis.MODEL, d)
    def endpoint(self, d: str) -> SearchEvent: return self.record(Axis.ENDPOINT, d)
    def hyperparam(self, d: str) -> SearchEvent: return self.record(Axis.HYPERPARAM, d)
    def seed(self, d: str) -> SearchEvent: return self.record(Axis.SEED, d)
    def exclusion(self, d: str) -> SearchEvent: return self.record(Axis.EXCLUSION, d)
    def metric(self, d: str) -> SearchEvent: return self.record(Axis.METRIC, d)
    def repair(self, d: str) -> SearchEvent: return self.record(Axis.REPAIR, d)

    def decision_after_data(self, d: str) -> SearchEvent:
        return self.record(Axis.DECISION_AFTER_DATA, d, after_seeing_data=True)

    # --- analysis ------------------------------------------------------------
    def distinct(self, axis: Axis) -> int:
        return len({e.detail for e in self.events if e.axis == axis})

    def degrees_of_freedom(self) -> dict[str, int]:
        return {a.value: self.distinct(a) for a in Axis if self.distinct(a)}

    def effective_comparisons(self) -> int:
        """Product of distinct choices across FORKING axes (≥1). The size of the
        garden of forking paths — how many analyses could have been the 'final' one."""
        n = 1
        for a in _FORKING:
            n *= max(1, self.distinct(a))
        return n

    def decisions_after_data(self) -> int:
        return sum(1 for e in self.events if e.after_seeing_data)

    def debt_level(self) -> str:
        n = self.effective_comparisons()
        if n <= 1:
            return "ninguna"
        if n <= 5:
            return "baja"
        if n <= 50:
            return "moderada"
        if n <= 1000:
            return "alta"
        return "severa"

    def suggested_alpha(self, alpha: float = 0.05) -> float:
        """Bonferroni-style ceiling as a COMMUNICATION device (not a magic fix):
        an honest reminder of how much smaller a 'significant' threshold must be."""
        return alpha / max(1, self.effective_comparisons())

    def classify_result(self, registry: ProtocolRegistry | None = None,
                        protocol_hash: str | None = None) -> tuple[Regime, str]:
        """A result is CONFIRMATION only if produced under a frozen, unblinded protocol.
        Anything decided after seeing the data is EXPLORATORY — enforced here, not hoped."""
        if registry is not None and protocol_hash \
                and registry.classify(protocol_hash) is Regime.CONFIRMATION:
            return Regime.CONFIRMATION, "protocolo congelado y datos confirmatorios revelados"
        if self.decisions_after_data():
            return Regime.DISCOVERY, (
                f"{self.decisions_after_data()} decisión(es) tras ver los datos → "
                f"exploratorio")
        return Regime.DISCOVERY, "sin protocolo confirmatorio congelado → exploratorio"

    def summary(self) -> dict[str, object]:
        return {
            "mission_id": self.mission_id,
            "degrees_of_freedom": self.degrees_of_freedom(),
            "effective_comparisons": self.effective_comparisons(),
            "decisions_after_data": self.decisions_after_data(),
            "exploration_debt": self.debt_level(),
            "suggested_alpha_0.05": round(self.suggested_alpha(), 6),
            "n_events": len(self.events),
        }
