"""Derivative estimation — several strategies, with error and unreliable regions.

No single strategy fits all cases; each records its method, parameters, an estimated
error, and which regions (edges, large gaps) are unreliable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class DerivativeResult:
    dydt: np.ndarray
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    estimated_error: float = 0.0
    unreliable_index: list[int] = field(default_factory=list)


def finite_difference(t: np.ndarray, y: np.ndarray) -> DerivativeResult:
    """Central differences on the interior, one-sided at the edges."""
    dydt = np.gradient(y, t)
    # Edges are less reliable; large gaps too.
    dt = np.diff(t)
    med = float(np.median(dt)) if len(dt) else 1.0
    unreliable = [0, len(y) - 1]
    unreliable += [int(i + 1) for i, d in enumerate(dt) if d > 3 * med]
    # crude error estimate: second difference magnitude scaled by dt
    err = float(np.mean(np.abs(np.gradient(dydt, t)))) * med
    return DerivativeResult(dydt=dydt, method="finite_difference",
                            estimated_error=round(err, 6),
                            unreliable_index=sorted(set(unreliable)))


def savgol_derivative(t: np.ndarray, y: np.ndarray, *, window: int = 11,
                      poly: int = 3) -> DerivativeResult:
    """Savitzky–Golay smoothing derivative (robust to noise). Falls back to finite
    differences if scipy is unavailable or the window is too large."""
    try:
        from scipy.signal import savgol_filter

        w = min(window, len(y) - (1 - len(y) % 2))
        if w < poly + 2:
            return finite_difference(t, y)
        if w % 2 == 0:
            w -= 1
        dt = float(np.median(np.diff(t)))
        dydt = savgol_filter(y, w, poly, deriv=1, delta=dt)
        return DerivativeResult(dydt=dydt, method="savitzky_golay",
                                params={"window": w, "poly": poly},
                                unreliable_index=[0, len(y) - 1])
    except Exception:  # pragma: no cover - depends on scipy
        return finite_difference(t, y)


def spline_derivative(t: np.ndarray, y: np.ndarray, *, smoothing: float | None = None
                      ) -> DerivativeResult:
    """Smoothing-spline derivative; falls back to finite differences without scipy."""
    try:
        from scipy.interpolate import UnivariateSpline

        s = smoothing if smoothing is not None else len(y) * float(np.var(y)) * 1e-3
        spl = UnivariateSpline(t, y, k=min(4, len(y) - 1), s=s)
        return DerivativeResult(dydt=spl.derivative()(t), method="spline",
                                params={"smoothing": s}, unreliable_index=[0, len(y) - 1])
    except Exception:  # pragma: no cover
        return finite_difference(t, y)


def estimate(t: np.ndarray, y: np.ndarray, *, method: str = "auto") -> DerivativeResult:
    """Pick a strategy. 'auto' uses Savitzky–Golay when data look noisy, else FD."""
    if method == "finite_difference":
        return finite_difference(t, y)
    if method == "savgol":
        return savgol_derivative(t, y)
    if method == "spline":
        return spline_derivative(t, y)
    # auto: estimate noise via lag-1 roughness
    rough = float(np.mean(np.abs(np.diff(y, n=2)))) if len(y) > 2 else 0.0
    scale = float(np.std(y)) + 1e-12
    return savgol_derivative(t, y) if rough / scale > 0.02 else finite_difference(t, y)
