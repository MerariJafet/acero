"""Regime / change-point detection (Sprint 8.8).

Detects whether a single global equation fails to describe the whole domain by
analysing the GLOBAL model's residuals across windows. A single regime yields
homogeneous residuals; a regime change yields a contiguous block of high residuals.
This is robust to periodic data (where local-coefficient methods false-positive).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..data.derivatives import estimate
from .sparse_identification import stlsq


def detect_change_points(t: np.ndarray, y: np.ndarray, theta: np.ndarray,
                         names: list[str], *, n_windows: int = 8, threshold: float = 0.2
                         ) -> dict[str, Any]:
    n = len(t)
    if n < 40 or n_windows < 3:
        return {"regime_change": False, "reason": "insufficient data", "regimes": []}
    d = estimate(t, y)
    xi = stlsq(theta, d.dydt, threshold=threshold)
    resid = np.abs(d.dydt - theta @ xi)
    scale = float(np.median(resid)) + 1e-9

    bounds = np.linspace(0, n, n_windows + 1).astype(int)
    win_resid = []
    for w in range(n_windows):
        sl = slice(bounds[w], bounds[w + 1])
        win_resid.append(float(np.median(resid[sl])) if bounds[w + 1] > bounds[w] else 0.0)
    win_resid_arr = np.array(win_resid)
    med = float(np.median(win_resid_arr))
    mad = float(np.median(np.abs(win_resid_arr - med))) + 1e-9

    # A window is "anomalous" if its residual is much larger than the median window.
    anomalous = [w for w in range(n_windows)
                 if win_resid_arr[w] > med + 5 * mad and win_resid_arr[w] > 3 * scale]
    # Require a CONTIGUOUS block (a genuine regime), not scattered noise.
    contiguous = _longest_contiguous(anomalous)
    regime_change = len(contiguous) >= 1 and len(anomalous) <= n_windows // 2

    regimes = []
    if regime_change:
        lo, hi = contiguous[0], contiguous[-1] + 1
        regimes = [
            {"window_range": [0, lo], "time_range": [float(t[0]), float(t[bounds[lo]])]},
            {"window_range": [lo, hi], "time_range": [float(t[bounds[lo]]),
                                                      float(t[bounds[min(hi, n_windows)] - 1])],
             "note": "high global-model residual -> different local dynamics"},
        ]
    return {"regime_change": bool(regime_change),
            "n_regimes": len(regimes) if regime_change else 1,
            "regimes": regimes,
            "window_residuals": [round(x, 5) for x in win_resid],
            "transition_evidence": round(float(win_resid_arr.max() / (med + 1e-9)), 3)}


def _longest_contiguous(indices: list[int]) -> list[int]:
    if not indices:
        return []
    indices = sorted(indices)
    best: list[int] = []
    cur = [indices[0]]
    for i in indices[1:]:
        if i == cur[-1] + 1:
            cur.append(i)
        else:
            if len(cur) > len(best):
                best = cur
            cur = [i]
    return cur if len(cur) > len(best) else best
