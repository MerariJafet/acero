"""Sparse system identification (Sprint 8.8).

A SINDy-inspired sequential thresholded least squares (STLSQ): fit dX/dt against a
library Θ(X), zero small coefficients, refit, iterate. We report stability across
thresholds, bootstrap resampling, and multiple seeds — NOT a single point estimate.
This is system identification, not "discovering a law": the library is IMPOSED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


def _normalize(theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    scales = np.linalg.norm(theta, axis=0)
    scales[scales == 0] = 1.0
    return theta / scales, scales


def _ridge(theta: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Ridge (Tikhonov) least squares — stabilises collinear libraries (e.g. when a
    conserved quantity makes {1, x^2, v^2} linearly dependent)."""
    p = theta.shape[1]
    a = theta.T @ theta + lam * np.eye(p)
    return np.linalg.solve(a, theta.T @ y)


def stlsq(theta: np.ndarray, dxdt: np.ndarray, *, threshold: float = 0.1,
          max_iter: int = 20, ridge: float = 1e-3) -> np.ndarray:
    """Sequential thresholded ridge regression on NORMALISED columns.

    Returns coefficients in the ORIGINAL (unnormalised) scale. Ridge suppresses the
    null-space blow-up from collinear terms so thresholding can remove them.
    """
    theta_n, scales = _normalize(theta)
    xi = _ridge(theta_n, dxdt, ridge)
    for _ in range(max_iter):
        small = np.abs(xi) < threshold
        if small.all():
            break
        big = ~small
        xi[small] = 0.0
        if big.any():
            xi[big] = _ridge(theta_n[:, big], dxdt, ridge)
        else:
            break
    return xi / scales


@dataclass
class IdentifiedEquation:
    target: str
    coefficients: dict[str, float]        # term name -> coefficient (thresholded)
    active_terms: list[str]
    rmse: float
    r2: float
    threshold: float
    n_samples: int
    stability: dict[str, float] = field(default_factory=dict)  # term -> selection frequency
    notes: str = ""

    def expression(self) -> str:
        parts = [f"{c:+.4g}·{t}" if t != "1" else f"{c:+.4g}"
                 for t, c in self.coefficients.items() if abs(c) > 0]
        return " ".join(parts) if parts else "0"


def _r2(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def identify(theta: np.ndarray, names: list[str], dxdt: np.ndarray, target: str, *,
             threshold: float = 0.1) -> IdentifiedEquation:
    xi = stlsq(theta, dxdt, threshold=threshold)
    coefs = {names[i]: float(xi[i]) for i in range(len(names)) if abs(xi[i]) > 1e-10}
    yhat = theta @ xi
    rmse = float(np.sqrt(np.mean((dxdt - yhat) ** 2)))
    return IdentifiedEquation(
        target=target, coefficients=coefs, active_terms=list(coefs),
        rmse=round(rmse, 6), r2=round(_r2(dxdt, yhat), 6), threshold=threshold,
        n_samples=len(dxdt))


def stability_selection(theta: np.ndarray, names: list[str], dxdt: np.ndarray, *,
                        thresholds: tuple[float, ...] = (0.02, 0.05, 0.1, 0.2, 0.5),
                        n_bootstrap: int = 20, seed: int = 0) -> dict[str, float]:
    """Fraction of (threshold × bootstrap) runs in which each term is selected."""
    rng = np.random.default_rng(seed)
    counts = {name: 0 for name in names}
    total = 0
    n = len(dxdt)
    for thr in thresholds:
        for _ in range(n_bootstrap):
            idx = rng.integers(0, n, size=n)
            xi = stlsq(theta[idx], dxdt[idx], threshold=thr)
            for i, name in enumerate(names):
                if abs(xi[i]) > 1e-8:
                    counts[name] += 1
            total += 1
    return {name: round(c / total, 4) for name, c in counts.items() if c > 0}


def threshold_sensitivity(theta: np.ndarray, names: list[str], dxdt: np.ndarray, *,
                          thresholds: tuple[float, ...] = (0.02, 0.05, 0.1, 0.2, 0.5)
                          ) -> dict[str, list[str]]:
    """Active term set as a function of the threshold (hyperparameter sensitivity)."""
    out: dict[str, list[str]] = {}
    for thr in thresholds:
        xi = stlsq(theta, dxdt, threshold=thr)
        out[str(thr)] = [names[i] for i in range(len(names)) if abs(xi[i]) > 1e-8]
    return out


def to_report(eqs: list[IdentifiedEquation]) -> dict[str, Any]:
    return {"equations": {e.target: {"expression": e.expression(),
                                     "coefficients": e.coefficients,
                                     "rmse": e.rmse, "r2": e.r2,
                                     "stability": e.stability} for e in eqs}}
