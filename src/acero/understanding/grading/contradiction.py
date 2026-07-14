"""Deterministic contradiction and prohibited-claim detection.

Independent of Codex: catches a response that both asserts and denies the same thing, and
reuses the misconception catalogue to flag forbidden conflations (e.g. "fit proves the
mechanism"). These are hard signals the aggregator treats as authority.
"""

from __future__ import annotations

import re

from ..learner.misconceptions import detect as detect_misconceptions

_CONTRADICTION_PAIRS = [
    ("is a law", "not a law"),
    ("is causal", "not causal"),
    ("is identifiable", "not identifiable"),
    ("proves", "does not prove"),
    ("is the mechanism", "not the mechanism"),
]


def has_self_contradiction(response: str) -> bool:
    low = " ".join(response.lower().split())
    for a, b in _CONTRADICTION_PAIRS:
        if a in low and b in low:
            return True
    # "X and not X" within one clause
    if re.search(r"\b(\w+)\b.*\bnot\b.*\b\1\b", low):
        # too broad on its own; only count when a known assertion word is negated nearby
        for kw in ("causal", "law", "identifiable", "mechanism"):
            if re.search(rf"{kw}.*\bnot\b.*{kw}", low):
                return True
    return False


def prohibited_claims(response: str, *, learner_id: str = "grader") -> list[str]:
    """Return misconception statements the response asserts (non-negated)."""
    return [m.statement for m in detect_misconceptions(response, learner_id=learner_id)]
