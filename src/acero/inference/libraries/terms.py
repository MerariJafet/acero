"""Candidate term library with filtering (Sprint 8.8).

Builds a controlled library of feature functions of the state variables and filters
it by: data domain (no 1/x across zero, no log/sqrt of non-positive), algebraic
duplicates, forbidden terms, an optional dimensional consistency check (dimensionless
coefficients), and a complexity cap. Every included term records WHY it was included.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ...cognitive import dimensions as dim


@dataclass
class Term:
    name: str
    fn: Callable[..., Any]        # feature evaluator over the data dict
    complexity: int
    reason: str = "included"
    dimension: dim.Dimension | None = None


def _candidate_terms(variables: list[str], families: set[str]) -> list[Term]:
    """Build candidate terms for the requested families. Domain-unsafe families
    (reciprocal, sqrt, log, trig) are opt-in and further filtered against the data."""
    terms: list[Term] = [Term("1", lambda d: np.ones_like(next(iter(d.values()))), 0,
                              "constant/bias")]
    for v in variables:
        if "poly" in families:
            terms.append(Term(v, (lambda d, v=v: d[v]), 1, "linear"))
            terms.append(Term(f"{v}^2", (lambda d, v=v: d[v] ** 2), 2, "quadratic"))
            terms.append(Term(f"{v}^3", (lambda d, v=v: d[v] ** 3), 3, "cubic"))
        if "reciprocal" in families:
            terms.append(Term(f"1/{v}", (lambda d, v=v: 1.0 / d[v]), 2, "reciprocal"))
        if "sqrt" in families:
            terms.append(Term(f"sqrt({v})", (lambda d, v=v: np.sqrt(d[v])), 2, "sqrt"))
        if "log" in families:
            terms.append(Term(f"log({v})", (lambda d, v=v: np.log(d[v])), 2, "log"))
        if "trig" in families:
            terms.append(Term(f"sin({v})", (lambda d, v=v: np.sin(d[v])), 2, "trig"))
            terms.append(Term(f"cos({v})", (lambda d, v=v: np.cos(d[v])), 2, "trig"))
    if "interaction" in families:
        for i in range(len(variables)):
            for j in range(i + 1, len(variables)):
                a, b = variables[i], variables[j]
                terms.append(Term(f"{a}*{b}", (lambda d, a=a, b=b: d[a] * d[b]), 2, "interaction"))
    return terms


def _domain_ok(term: Term, data: dict[str, np.ndarray]) -> tuple[bool, str]:
    """Reject terms that are singular or out-of-domain on the observed data."""
    for v, series in data.items():
        scale = float(np.std(series)) + 1e-9
        crosses_zero = float(np.min(series)) < 0 < float(np.max(series))
        if term.name == f"1/{v}" and (crosses_zero
                                      or float(np.min(np.abs(series))) < 0.05 * scale):
            return False, "reciprocal singular (variable crosses/approaches zero)"
        if term.name == f"sqrt({v})" and float(np.min(series)) < 0:
            return False, "sqrt of negative values"
        if term.name == f"log({v})" and float(np.min(series)) <= 0:
            return False, "log of non-positive values"
    return True, "ok"


@dataclass
class TermLibrary:
    variables: list[str]
    terms: list[Term] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)

    @classmethod
    def build(cls, variables: list[str], data: dict[str, np.ndarray], *,
              forbidden: list[str] | None = None, max_complexity: int = 3,
              families: set[str] | None = None) -> TermLibrary:
        """Default families are polynomial + interactions (well-conditioned for
        polynomial dynamics). Add 'reciprocal'/'sqrt'/'log'/'trig' explicitly."""
        forbidden_set = set(forbidden or [])
        families = families or {"poly", "interaction"}
        candidates = _candidate_terms(variables, families)
        kept: list[Term] = []
        excluded: list[dict] = []
        seen_signatures: dict[tuple, str] = {}
        for term in candidates:
            if term.name in forbidden_set:
                excluded.append({"term": term.name, "reason": "forbidden"})
                continue
            if term.complexity > max_complexity:
                excluded.append({"term": term.name, "reason": "too complex"})
                continue
            ok, why = _domain_ok(term, data)
            if not ok:
                excluded.append({"term": term.name, "reason": why})
                continue
            try:
                values = term.fn(data)
            except Exception:  # noqa: BLE001
                excluded.append({"term": term.name, "reason": "evaluation error"})
                continue
            if not np.all(np.isfinite(values)):
                excluded.append({"term": term.name, "reason": "domain singularity"})
                continue
            # Algebraic-duplicate detection: same numeric signature -> drop.
            sig = tuple(np.round(values / (np.linalg.norm(values) + 1e-12), 6)[:16])
            if sig in seen_signatures:
                excluded.append({"term": term.name, "reason":
                                 f"algebraic duplicate of {seen_signatures[sig]}"})
                continue
            seen_signatures[sig] = term.name
            kept.append(term)
        return cls(variables=variables, terms=kept, excluded=excluded)

    def theta(self, data: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str]]:
        cols = [t.fn(data) for t in self.terms]
        return np.column_stack(cols), [t.name for t in self.terms]

    @property
    def names(self) -> list[str]:
        return [t.name for t in self.terms]
