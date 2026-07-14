"""Hypothesis tournament: multiobjective ranking with pairwise Elo (Sprint 5.6).

There is NO single opaque score. Every candidate gets a transparent vector of
objective scores; the final ranking combines a documented weighted sum with
pairwise Elo (whose every comparison is retained). An LLM may critique candidates,
but the ranking itself is produced by deterministic rules — the LLM is advisory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .candidates import HypothesisCandidate, HypothesisType
from .diversity import DiversityReport, analyze
from .falsifiability import score_candidate

# Documented default weights (auditable; overridable).
DEFAULT_WEIGHTS = {
    "falsifiability": 0.30,
    "actionability": 0.15,
    "specificity": 0.15,
    "low_assumption_burden": 0.10,
    "diversity_contribution": 0.15,
    "feasibility": 0.10,
    "novelty": 0.05,
}


@dataclass
class ObjectiveScores:
    candidate_id: str
    objectives: dict[str, float]
    weighted: float

    def as_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id,
                "objectives": {k: round(v, 4) for k, v in self.objectives.items()},
                "weighted": round(self.weighted, 4)}


@dataclass
class Comparison:
    a: str
    b: str
    winner: str
    margin: float
    basis: str


@dataclass
class TournamentResult:
    ranking: list[str]
    scores: dict[str, ObjectiveScores]
    elo: dict[str, float]
    comparisons: list[Comparison]
    weights: dict[str, float]
    diversity: DiversityReport
    llm_critique: dict[str, Any] | None = field(default=None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ranking": self.ranking,
            "weights": self.weights,
            "elo": {k: round(v, 1) for k, v in self.elo.items()},
            "scores": {k: v.as_dict() for k, v in self.scores.items()},
            "comparisons": [c.__dict__ for c in self.comparisons],
            "diversity": self.diversity.as_dict(),
            "llm_critique": self.llm_critique,
        }


def _feasibility(c: HypothesisCandidate) -> float:
    cpu = float(c.estimated_compute.get("cpu_seconds", 5))
    # Cheaper -> more feasible; saturating.
    return 1.0 / (1.0 + cpu / 30.0)


def _novelty(c: HypothesisCandidate) -> float:
    # Heuristic preliminary novelty: mechanistic/analogical > predictive > baseline/null.
    table = {
        HypothesisType.MECHANISTIC: 0.7, HypothesisType.CAUSAL: 0.8,
        HypothesisType.ANALOGICAL: 0.8, HypothesisType.MATHEMATICAL: 0.6,
        HypothesisType.PREDICTIVE: 0.4, HypothesisType.COMPUTATIONAL: 0.4,
        HypothesisType.DESCRIPTIVE: 0.3, HypothesisType.BOUNDARY_CASE: 0.5,
        HypothesisType.NULL: 0.1, HypothesisType.BASELINE: 0.1,
    }
    return table.get(c.hypothesis_type, 0.4)


def score_objectives(
    candidates: list[HypothesisCandidate],
    diversity: DiversityReport,
    weights: dict[str, float] | None = None,
) -> dict[str, ObjectiveScores]:
    weights = weights or DEFAULT_WEIGHTS
    # Diversity contribution: candidates in smaller mechanism clusters are rarer.
    cluster_of: dict[str, int] = {}
    for cluster in diversity.mechanism_clusters:
        for cid in cluster:
            cluster_of[cid] = len(cluster)

    out: dict[str, ObjectiveScores] = {}
    for c in candidates:
        f = score_candidate(c)
        div_contrib = 1.0 / cluster_of.get(c.id, 1)
        objectives = {
            "falsifiability": f.falsifiability_score,
            "actionability": f.actionability_score,
            "specificity": f.specificity_score,
            "low_assumption_burden": 1.0 - f.assumption_burden,
            "diversity_contribution": div_contrib,
            "feasibility": _feasibility(c),
            "novelty": _novelty(c),
        }
        weighted = sum(weights.get(k, 0.0) * v for k, v in objectives.items())
        out[c.id] = ObjectiveScores(candidate_id=c.id, objectives=objectives, weighted=weighted)
    return out


def _elo_update(ra: float, rb: float, a_wins: bool, k: float = 24.0) -> tuple[float, float]:
    ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400))
    sa = 1.0 if a_wins else 0.0
    ra2 = ra + k * (sa - ea)
    rb2 = rb + k * ((1 - sa) - (1 - ea))
    return ra2, rb2


def run_tournament(
    candidates: list[HypothesisCandidate],
    weights: dict[str, float] | None = None,
    llm_critique: dict[str, Any] | None = None,
) -> TournamentResult:
    weights = weights or DEFAULT_WEIGHTS
    diversity = analyze(candidates)
    scores = score_objectives(candidates, diversity, weights)

    elo: dict[str, float] = {c.id: 1000.0 for c in candidates}
    comparisons: list[Comparison] = []
    # Deterministic round-robin: higher weighted multiobjective score wins each pair.
    ids = [c.id for c in candidates]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            sa, sb = scores[a].weighted, scores[b].weighted
            a_wins = sa >= sb
            winner = a if a_wins else b
            elo[a], elo[b] = _elo_update(elo[a], elo[b], a_wins)
            comparisons.append(Comparison(
                a=a, b=b, winner=winner, margin=round(abs(sa - sb), 4),
                basis="weighted_multiobjective",
            ))

    # Final ranking: primary by weighted score, tie-break by Elo. Deterministic.
    ranking = sorted(ids, key=lambda cid: (scores[cid].weighted, elo[cid]), reverse=True)
    return TournamentResult(
        ranking=ranking, scores=scores, elo=elo, comparisons=comparisons,
        weights=weights, diversity=diversity, llm_critique=llm_critique,
    )
