"""Confidence updates after an experiment (Sprint 7.5).

Two clearly-separated modes:
  * Bayesian update — ONLY when genuine likelihoods P(observed_outcome | hypothesis)
    exist. Returns a posterior distribution.
  * Ordinal update — when probabilities are not justified. Moves a hypothesis along a
    labelled ordinal scale. NEVER dressed up as a calibrated probability.

An LLM's stated 'confidence' is never accepted as a scientific probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConfidenceLevel(int, Enum):
    REFUTED = 0
    WEAKENED = 1
    NEUTRAL = 2
    SUPPORTED = 3
    STRONGLY_SUPPORTED = 4


@dataclass
class ResultQuality:
    quality: float          # [0,1] overall result quality
    reproducible: bool
    discriminating: bool

    @property
    def trustworthy(self) -> bool:
        return self.quality >= 0.5 and self.reproducible


def assess_result_quality(result: dict[str, Any]) -> ResultQuality:
    reproducible = bool(result.get("reproduced", False))
    discriminating = bool(result.get("discriminating", False))
    ok = result.get("status", "ok") == "ok"
    quality = 0.0
    if ok:
        quality += 0.4
    if reproducible:
        quality += 0.4
    if discriminating:
        quality += 0.2
    return ResultQuality(quality=round(quality, 4), reproducible=reproducible,
                         discriminating=discriminating)


def _normalise(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values())
    if total <= 0:
        n = len(d)
        return {k: 1.0 / n for k in d} if n else {}
    return {k: v / total for k, v in d.items()}


@dataclass
class BayesianUpdate:
    prior: dict[str, float]
    posterior: dict[str, float]
    method: str = "bayesian"

    def as_dict(self) -> dict[str, Any]:
        return {"method": self.method,
                "prior": {k: round(v, 4) for k, v in self.prior.items()},
                "posterior": {k: round(v, 4) for k, v in self.posterior.items()}}


def bayesian_update(prior: dict[str, float],
                    likelihood: dict[str, float]) -> BayesianUpdate:
    """posterior[h] ∝ prior[h] * P(observed_outcome | h)."""
    prior_n = _normalise(prior)
    post = {h: prior_n.get(h, 0.0) * likelihood.get(h, 0.0) for h in prior_n}
    if sum(post.values()) <= 0:
        post = dict(prior_n)  # uninformative observation; keep prior
    return BayesianUpdate(prior=prior_n, posterior=_normalise(post))


@dataclass
class OrdinalUpdate:
    hypothesis_id: str
    previous: ConfidenceLevel
    updated: ConfidenceLevel
    method: str = "ordinal"
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"method": self.method, "hypothesis_id": self.hypothesis_id,
                "previous": self.previous.name, "updated": self.updated.name,
                "reason": self.reason}


def ordinal_update(hypothesis_id: str, current: ConfidenceLevel, outcome: str,
                   quality: ResultQuality) -> OrdinalUpdate:
    """Move a hypothesis along the ordinal scale based on the experiment outcome.

    outcome: 'supported' | 'weakened' | 'refuted' | 'inconclusive'.
    Low-quality/non-reproducible results move confidence LESS (or not at all).
    """
    step = 1 if quality.trustworthy else 0
    level = int(current)
    reason = f"outcome={outcome}, quality={quality.quality}, reproducible={quality.reproducible}"
    if outcome == "refuted":
        level = int(ConfidenceLevel.REFUTED) if quality.trustworthy else max(0, level - 1)
    elif outcome == "weakened":
        level = max(int(ConfidenceLevel.REFUTED), level - step)
    elif outcome == "supported":
        level = min(int(ConfidenceLevel.STRONGLY_SUPPORTED), level + step)
    else:  # inconclusive
        reason += " (inconclusive: no change)"
    return OrdinalUpdate(hypothesis_id=hypothesis_id, previous=current,
                         updated=ConfidenceLevel(level), reason=reason)


def which_weakens(posterior_or_levels: dict[str, float]) -> list[str]:
    """Return ids below the mean (the ones an update weakens). Works for probs or levels."""
    if not posterior_or_levels:
        return []
    mean = sum(posterior_or_levels.values()) / len(posterior_or_levels)
    return sorted([k for k, v in posterior_or_levels.items() if v < mean])
