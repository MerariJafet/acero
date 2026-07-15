"""Portfolio prioritization (Sprint 16).

Scores candidate subprojects across SEVERAL dimensions and returns the full profile — never a
single opaque number. A ranking is offered, but every dimension stays visible so a human can
override it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DIMENSIONS = (
    "information_gain", "feasibility", "novelty_uncertainty", "compute_cost",
    "learning_value", "data_available", "risk", "dependency_readiness",
    "external_validation_need",
)

# Direction: +1 = higher is better, -1 = higher is worse (cost/risk/uncertainty/ext-need).
_DIRECTION = {
    "information_gain": 1, "feasibility": 1, "novelty_uncertainty": -1, "compute_cost": -1,
    "learning_value": 1, "data_available": 1, "risk": -1, "dependency_readiness": 1,
    "external_validation_need": -1,
}


@dataclass
class ProjectScore:
    project_id: str
    dimensions: dict[str, float]                       # each in [0,1]
    composite_view: float = 0.0
    rationale: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"project_id": self.project_id, "dimensions": self.dimensions,
                "composite_view": self.composite_view, "rationale": self.rationale}


@dataclass
class Portfolio:
    scores: list[ProjectScore] = field(default_factory=list)

    def add(self, project_id: str, dims: dict[str, float], *, rationale: str = "") -> ProjectScore:
        clean = {d: max(0.0, min(1.0, float(dims.get(d, 0.5)))) for d in DIMENSIONS}
        # composite is a VIEW (mean of direction-adjusted dims), not a verdict
        adj = [(v if _DIRECTION[d] > 0 else 1 - v) for d, v in clean.items()]
        score = ProjectScore(project_id, clean, round(sum(adj) / len(adj), 4), rationale)
        self.scores.append(score)
        return score

    def ranked(self) -> list[ProjectScore]:
        """Ranked by composite VIEW; dimensions remain visible for human override."""
        return sorted(self.scores, key=lambda s: s.composite_view, reverse=True)

    def as_dict(self) -> dict[str, Any]:
        return {"dimensions": list(DIMENSIONS),
                "ranking": [s.as_dict() for s in self.ranked()],
                "note": "composite_view is a mean, NOT a single trust/priority verdict; "
                        "every dimension is shown so a human can override the ordering."}
