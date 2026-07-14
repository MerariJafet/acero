"""Expected Information Gain (Sprint 6.3).

When a probabilistic model exists, EIG = H(prior) - E_outcome[H(posterior|outcome)]
over hypotheses. When it does not, we fall back to an EXPLICIT, documented heuristic
and say so — we never fabricate precise probabilities. Priors can be uniform, human,
or model-suggested; sensitivity to the prior is reported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def entropy(probs: dict[str, float]) -> float:
    total = sum(probs.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for p in probs.values():
        q = p / total
        if q > 0:
            h -= q * math.log2(q)
    return h


def _normalise(d: dict[str, float]) -> dict[str, float]:
    total = sum(d.values())
    if total <= 0:
        n = len(d)
        return {k: 1.0 / n for k in d} if n else {}
    return {k: v / total for k, v in d.items()}


@dataclass
class EIGResult:
    method: str            # "bayesian" | "heuristic"
    eig: float
    prior_entropy: float
    expected_posterior_entropy: float
    detail: dict

    def as_dict(self) -> dict:
        return {
            "method": self.method,
            "eig": round(self.eig, 4),
            "prior_entropy": round(self.prior_entropy, 4),
            "expected_posterior_entropy": round(self.expected_posterior_entropy, 4),
            "detail": self.detail,
        }


def bayesian_eig(
    prior: dict[str, float],
    likelihoods: dict[str, dict[str, float]],
) -> EIGResult:
    """EIG over hypotheses given per-hypothesis outcome likelihoods.

    prior: {hypothesis_id: P(hyp)}.
    likelihoods: {hypothesis_id: {outcome: P(outcome | hyp)}}.
    """
    prior = _normalise(prior)
    h_prior = entropy(prior)

    # Enumerate the outcome space.
    outcomes: set[str] = set()
    for od in likelihoods.values():
        outcomes.update(od.keys())

    # P(outcome) = sum_h prior[h] * P(outcome|h)
    p_outcome: dict[str, float] = {o: 0.0 for o in outcomes}
    for h, ph in prior.items():
        od = _normalise(likelihoods.get(h, {}))
        for o in outcomes:
            p_outcome[o] += ph * od.get(o, 0.0)

    expected_post_h = 0.0
    per_outcome = {}
    for o in outcomes:
        if p_outcome[o] <= 0:
            continue
        # posterior[h|o] ∝ prior[h] * P(o|h)
        post = {}
        for h, ph in prior.items():
            od = _normalise(likelihoods.get(h, {}))
            post[h] = ph * od.get(o, 0.0)
        post = _normalise(post)
        h_post = entropy(post)
        expected_post_h += p_outcome[o] * h_post
        per_outcome[o] = {"p_outcome": round(p_outcome[o], 4), "posterior_entropy": round(h_post, 4)}

    eig = max(0.0, h_prior - expected_post_h)
    return EIGResult("bayesian", eig, h_prior, expected_post_h,
                     {"p_outcome": {k: round(v, 4) for k, v in p_outcome.items()},
                      "per_outcome": per_outcome})


def heuristic_eig(n_hypotheses: int, distinct_outcomes: int) -> EIGResult:
    """Documented fallback when no probabilities exist.

    Idea: an experiment that splits n hypotheses into k distinct outcome-groups can
    reduce at most log2(k) bits (best case: equal groups). This is an UPPER-BOUND
    heuristic, not a calibrated estimate.
    """
    h_prior = math.log2(n_hypotheses) if n_hypotheses > 0 else 0.0
    reducible = math.log2(distinct_outcomes) if distinct_outcomes > 0 else 0.0
    eig = min(h_prior, reducible)
    return EIGResult("heuristic", eig, h_prior, max(0.0, h_prior - eig),
                     {"note": "upper-bound heuristic: log2(distinct_outcomes)",
                      "n_hypotheses": n_hypotheses, "distinct_outcomes": distinct_outcomes})


def prior_sensitivity(
    likelihoods: dict[str, dict[str, float]],
    priors: dict[str, dict[str, float]],
) -> dict[str, object]:
    """Compute EIG under several named priors and report the range.

    priors: {prior_name: {hypothesis_id: P(hyp)}}.
    """
    results = {name: bayesian_eig(p, likelihoods).eig for name, p in priors.items()}
    values = list(results.values())
    return {
        "per_prior_eig": {k: round(v, 4) for k, v in results.items()},
        "min": round(min(values), 4) if values else 0.0,
        "max": round(max(values), 4) if values else 0.0,
        "range": round((max(values) - min(values)), 4) if values else 0.0,
    }


def uniform_prior(hypothesis_ids: list[str]) -> dict[str, float]:
    n = len(hypothesis_ids)
    return {h: 1.0 / n for h in hypothesis_ids} if n else {}
