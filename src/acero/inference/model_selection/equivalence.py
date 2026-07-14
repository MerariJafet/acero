"""Model equivalence (Sprint 8.8/8.9).

Detects models that are algebraically equivalent, equivalent only within the observed
range, or that diverge out of sample. Equivalent expressions are NOT counted as
distinct discoveries.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np


def algebraically_equivalent(coefs_a: dict[str, float], coefs_b: dict[str, float], *,
                             rel_tol: float = 0.05) -> bool:
    """Same active terms with coefficients within rel_tol."""
    if set(coefs_a) != set(coefs_b):
        return False
    for term in coefs_a:
        a, b = coefs_a[term], coefs_b[term]
        if abs(a - b) > rel_tol * (abs(a) + abs(b) + 1e-9):
            return False
    return True


def observationally_equivalent(pred_a: np.ndarray, pred_b: np.ndarray, y: np.ndarray, *,
                               rel_tol: float = 0.1) -> bool:
    """Two models are observationally equivalent on the data if their RMSEs are within
    rel_tol of each other AND their predictions barely differ."""
    def rmse(p):
        return float(np.sqrt(np.mean((p - y) ** 2)))
    ra, rb = rmse(pred_a), rmse(pred_b)
    spread = abs(ra - rb) / (min(ra, rb) + 1e-9)
    mutual = float(np.sqrt(np.mean((pred_a - pred_b) ** 2))) / (np.std(y) + 1e-9)
    return spread < rel_tol and mutual < rel_tol


def divergence_region(model_a: Callable[[np.ndarray], np.ndarray],
                      model_b: Callable[[np.ndarray], np.ndarray],
                      x_grid: np.ndarray) -> dict[str, Any]:
    """Where (over a grid, typically out of sample) do two models diverge most?"""
    pa = np.asarray(model_a(x_grid), dtype=float)
    pb = np.asarray(model_b(x_grid), dtype=float)
    diff = np.abs(pa - pb)
    i = int(np.argmax(diff))
    return {"max_divergence": float(diff[i]), "at": float(x_grid[i]),
            "mean_divergence": float(np.mean(diff)),
            "diverges": float(np.max(diff)) > 3 * float(np.mean(diff) + 1e-12)}


def cluster_equivalent(models: dict[str, dict[str, float]]) -> list[list[str]]:
    """Group model ids whose coefficient dicts are algebraically equivalent."""
    ids = list(models)
    groups: list[list[str]] = []
    used: set[str] = set()
    for i, a in enumerate(ids):
        if a in used:
            continue
        group = [a]
        used.add(a)
        for b in ids[i + 1:]:
            if b not in used and algebraically_equivalent(models[a], models[b]):
                group.append(b)
                used.add(b)
        groups.append(group)
    return groups
