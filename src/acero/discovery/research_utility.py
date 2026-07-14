"""Research utility: transparent multiobjective prioritisation (Sprint 6.4).

The utility is NEVER collapsed silently into one number. We expose the components,
the weights, the normalisation, the resulting score, and the sensitivity to weights.
It is a configurable heuristic, not a scientific truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BENEFIT_KEYS = (
    "information_gain", "scientific_value", "falsification_power",
    "reproducibility", "human_learning_value",
)
COST_KEYS = ("compute_cost", "time_cost", "monetary_cost", "risk")

DEFAULT_WEIGHTS = {
    "information_gain": 0.30,
    "scientific_value": 0.20,
    "falsification_power": 0.20,
    "reproducibility": 0.15,
    "human_learning_value": 0.15,
    "compute_cost": 0.4,
    "time_cost": 0.2,
    "monetary_cost": 0.3,
    "risk": 0.3,
}


@dataclass
class UtilityBreakdown:
    utility: float
    weighted_benefit: float
    weighted_cost: float
    components: dict[str, float]
    weights: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "utility": round(self.utility, 4),
            "weighted_benefit": round(self.weighted_benefit, 4),
            "weighted_cost": round(self.weighted_cost, 4),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "weights": self.weights,
        }


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compute_utility(components: dict[str, float],
                    weights: dict[str, float] | None = None) -> UtilityBreakdown:
    """Utility = weighted_benefit / (1 + weighted_cost). All parts are surfaced.

    Components are expected in [0,1]; monetary_cost is expected already normalised
    (0 = free). Costs raise the denominator rather than being hidden in a sum.
    """
    weights = weights or DEFAULT_WEIGHTS
    comp = {k: _clip01(float(components.get(k, 0.0))) for k in (*BENEFIT_KEYS, *COST_KEYS)}
    weighted_benefit = sum(weights.get(k, 0.0) * comp[k] for k in BENEFIT_KEYS)
    weighted_cost = sum(weights.get(k, 0.0) * comp[k] for k in COST_KEYS)
    utility = weighted_benefit / (1.0 + weighted_cost)
    return UtilityBreakdown(utility, weighted_benefit, weighted_cost, comp, weights)


def rank(candidates: dict[str, dict[str, float]],
         weights: dict[str, float] | None = None) -> list[tuple[str, UtilityBreakdown]]:
    """Rank {id: components} by utility. Returns list of (id, breakdown) desc."""
    scored = [(cid, compute_utility(comp, weights)) for cid, comp in candidates.items()]
    scored.sort(key=lambda t: t[1].utility, reverse=True)
    return scored


def weight_sensitivity(candidates: dict[str, dict[str, float]],
                       weight_variants: dict[str, dict[str, float]]) -> dict[str, Any]:
    """Report the top-ranked id under each weight variant and whether it is stable."""
    tops: dict[str, str] = {}
    for name, w in weight_variants.items():
        ranked = rank(candidates, w)
        tops[name] = ranked[0][0] if ranked else ""
    stable = len(set(tops.values())) == 1
    return {"top_by_variant": tops, "stable_top_choice": stable}
