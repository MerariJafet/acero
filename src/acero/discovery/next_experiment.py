"""Recommend the next best experiment (Sprint 7.8).

Chooses the experiment that best reduces uncertainty per unit cost, and ALWAYS
offers at least one alternative plus an explicit reason not to run the top pick.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .research_utility import compute_utility


class RecommendedNextExperiment(BaseModel):
    experiment_id: str
    reason: str
    expected_information_gain: float
    cost: float
    hypotheses_discriminated: list[str] = Field(default_factory=list)
    risk: float = 0.0
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    reason_not_to_run: str = ""


def recommend_next(candidates: list[dict[str, Any]],
                   weights: dict[str, float] | None = None) -> RecommendedNextExperiment | None:
    """candidates: list of dicts with keys:
        experiment_id, eig, cost, risk, hypotheses_discriminated, components (utility inputs).
    Ranks by research utility; returns top with >=1 alternative.
    """
    if not candidates:
        return None
    scored = []
    for c in candidates:
        util = compute_utility(c.get("components", {}), weights)
        scored.append((c, util.utility))
    scored.sort(key=lambda t: t[1], reverse=True)

    top, top_u = scored[0]
    alternatives = [
        {"experiment_id": c["experiment_id"], "utility": round(u, 4),
         "eig": c.get("eig"), "cost": c.get("cost")}
        for c, u in scored[1:4]
    ]
    reason_not = ""
    if top.get("risk", 0.0) >= 0.7:
        reason_not = "High risk; a human may prefer a safer alternative."
    elif top.get("cost", 0.0) >= 0.8:
        reason_not = "High cost; the marginal information may not justify it."
    else:
        reason_not = "None material; top pick dominates on utility."

    return RecommendedNextExperiment(
        experiment_id=top["experiment_id"],
        reason=f"Highest research utility ({top_u:.3f}); "
               f"discriminates {len(top.get('hypotheses_discriminated', []))} hypotheses.",
        expected_information_gain=float(top.get("eig", 0.0)),
        cost=float(top.get("cost", 0.0)),
        hypotheses_discriminated=list(top.get("hypotheses_discriminated", [])),
        risk=float(top.get("risk", 0.0)),
        alternatives=alternatives,
        reason_not_to_run=reason_not,
    )
