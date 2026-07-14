"""Invariant / conservation discovery (Sprint 8.8).

Finds combinations of library terms that stay (approximately) constant along the
trajectory — the low-variance directions of the feature covariance. Distinguishes
exact / approximate invariants from numerical artifacts and dataset-specific
regularities, and reports robustness to noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class InvariantCandidate:
    combination: dict[str, float]      # term name -> coefficient (unit-normalised)
    relative_variation: float          # std(Q) / (mean|Q| + eps)
    classification: str                # exact | approximate | artifact | dataset_specific
    expression: str


def _classify(rel_var: float) -> str:
    if rel_var < 0.01:
        return "exact"
    if rel_var < 0.1:
        return "approximate"
    if rel_var < 0.5:
        return "dataset_specific"
    return "artifact"


def find_invariants(theta: np.ndarray, names: list[str], *, top_k: int = 2
                    ) -> list[InvariantCandidate]:
    """Smallest-variance combinations of centred features are conserved quantities.

    The constant/bias term '1' is excluded — it is trivially conserved and would be a
    false invariant.
    """
    keep = [i for i, n in enumerate(names) if n != "1"]
    if len(keep) < 2:
        return []
    theta = theta[:, keep]
    names = [names[i] for i in keep]
    centred = theta - theta.mean(axis=0, keepdims=True)
    # Normalise columns so the combination is scale-aware.
    scales = np.linalg.norm(centred, axis=0)
    scales[scales == 0] = 1.0
    cn = centred / scales
    cov = cn.T @ cn / len(cn)
    eigvals, eigvecs = np.linalg.eigh(cov)
    out: list[InvariantCandidate] = []
    for k in range(min(top_k, len(eigvals))):
        vec = eigvecs[:, k] / scales
        q = theta @ vec
        rel = float(np.std(q) / (np.mean(np.abs(q)) + 1e-9))
        combo = {names[i]: round(float(vec[i]), 5) for i in range(len(names))
                 if abs(vec[i]) > 1e-3 * np.max(np.abs(vec))}
        expr = " ".join(f"{c:+.3g}·{t}" for t, c in combo.items())
        out.append(InvariantCandidate(combination=combo, relative_variation=round(rel, 5),
                                      classification=_classify(rel), expression=expr))
    out.sort(key=lambda c: c.relative_variation)
    return out


def verify_under_noise(theta_clean: np.ndarray, theta_noisy: np.ndarray, names: list[str],
                       candidate: InvariantCandidate) -> dict[str, Any]:
    """An invariant should survive (moderate) noise. Compare relative variation."""
    vec = np.array([candidate.combination.get(n, 0.0) for n in names])
    q_noisy = theta_noisy @ vec
    rel_noisy = float(np.std(q_noisy) / (np.mean(np.abs(q_noisy)) + 1e-9))
    return {"clean_relative_variation": candidate.relative_variation,
            "noisy_relative_variation": round(rel_noisy, 5),
            "survives_noise": rel_noisy < 0.2}
