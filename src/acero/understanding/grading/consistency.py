"""Consistency with the learner's prior responses.

Detects (a) copy-paste of a previous answer (low originality) and (b) a reversal that
contradicts an earlier, well-evidenced answer on the same concept. Deterministic; used as
a signal by the aggregator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


def _tokens(text: str) -> set[str]:
    return {w for w in re.split(r"\W+", text.lower()) if len(w) > 2}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


@dataclass
class ConsistencyResult:
    originality: float          # 1 - max similarity to prior responses
    repeats_prior: bool
    contradicts_prior: bool
    note: str = ""


def check(response: str, prior_responses: list[str], *,
          prior_asserted_not_law: bool = False) -> ConsistencyResult:
    sims = [_jaccard(response, p) for p in prior_responses]
    max_sim = max(sims) if sims else 0.0
    repeats = max_sim > 0.9
    low = response.lower()
    # a reversal: previously said "not a law", now says "is a law"
    contradicts = prior_asserted_not_law and ("is a law" in low and "not a law" not in low)
    return ConsistencyResult(
        originality=round(1 - max_sim, 4), repeats_prior=repeats,
        contradicts_prior=contradicts,
        note="repeat of a prior answer" if repeats else "")
