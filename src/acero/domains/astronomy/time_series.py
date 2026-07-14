"""Astronomy time-series methods.

Lomb–Scargle for unevenly sampled data, autocorrelation, a simple false-alarm heuristic,
and helpers for aliasing and red noise. A periodic peak is a PATTERN — never, by itself, a
mechanism.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import lombscargle


def lomb_scargle_period(t: np.ndarray, y: np.ndarray,
                        p_min: float = 0.2, p_max: float = 100.0, n: int = 4000
                        ) -> tuple[float, float]:
    """Return (best_period, normalized_power) using the Lomb–Scargle periodogram."""
    y = y - np.mean(y)
    periods = np.linspace(p_min, p_max, n)
    ang = 2 * np.pi / periods
    power = lombscargle(t.astype(float), y.astype(float), ang, normalize=True)
    i = int(np.argmax(power))
    return float(periods[i]), float(power[i])


def false_alarm_low(power: float, *, threshold: float = 0.5) -> bool:
    """Crude FAP flag: a low normalized power means the peak may be noise. WARNING only —
    a real FAP needs the sampling window and noise model."""
    return power < threshold


def autocorr_period(t: np.ndarray, y: np.ndarray) -> float:
    """Estimate a period from the first autocorrelation peak (uniform resampling)."""
    tt = np.linspace(t.min(), t.max(), len(t))
    yy = np.interp(tt, t, y)
    yy = yy - yy.mean()
    ac = np.correlate(yy, yy, mode="full")[len(yy) - 1:]
    ac /= ac[0]
    # first local max after the zero lag
    for i in range(1, len(ac) - 1):
        if ac[i] > ac[i - 1] and ac[i] > ac[i + 1] and ac[i] > 0.2:
            return float(tt[i] - tt[0])
    return float("nan")


def has_gaps(t: np.ndarray, *, factor: float = 5.0) -> bool:
    dts = np.diff(np.sort(t))
    return bool(dts.max() > factor * np.median(dts))
