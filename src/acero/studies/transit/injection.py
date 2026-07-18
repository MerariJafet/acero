"""Signal injection + recovery characterization.

Injects synthetic box transits (various depth/period/duration/phase/SNR) into a
signal-free baseline and measures recovery rate, period error, calibration, and
the false-positive rate on matched nulls. An injected signal recovered here is a
TEST of the pipeline — it is not an astrophysical observation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from . import pipelines as pl


def inject_box(time: np.ndarray, flux: np.ndarray, *, period: float, depth: float,
               duration_hours: float, phase: float = 0.0) -> np.ndarray:
    """Multiply a box-shaped transit into the light curve."""
    dur_days = duration_hours / 24.0
    ph = (((time - time[0]) / period) + phase) % 1.0
    half = (dur_days / period) / 2.0
    in_transit = (ph < half) | (ph > 1 - half)
    out = np.copy(flux)
    out[in_transit] *= (1.0 - depth)
    return out


def _baseline(n: int, rng: np.random.Generator, noise: float = 0.0017,
              trend: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """A signal-free baseline: cadence-like time + white noise (+ optional trend)."""
    time = np.cumsum(rng.uniform(0.019, 0.021, n))     # ~29.4 min cadence
    time -= time[0]
    flux = 1.0 + rng.normal(0, noise, n)
    if trend:
        flux += trend * (time - time.mean()) / (time[-1] - time[0])
    return time, flux


def recovery_grid(*, depths: list[float], periods: list[float],
                  durations_hours: list[float], phases: list[float],
                  n_points: int = 3000, noise: float = 0.0017, seed: int = 7,
                  tol_frac: float = 0.01) -> dict[str, Any]:
    """Inject over a grid; measure recovery rate and period error (Pipeline A)."""
    rng = np.random.default_rng(seed)
    cases = []
    recovered = 0
    period_errs = []
    for depth in depths:
        for period in periods:
            for dur in durations_hours:
                for phase in phases:
                    time, base = _baseline(n_points, rng, noise=noise)
                    inj = inject_box(time, base, period=period, depth=depth,
                                     duration_hours=dur, phase=phase)
                    res = pl.pipeline_a(time, inj, window=51, p_min=0.5,
                                        p_max=min(10.0, (time[-1] - time[0]) / 2))
                    err = abs(res.period - period) / period
                    ok = err < tol_frac and res.snr >= 7.0
                    if ok:
                        recovered += 1
                        period_errs.append(err)
                    # rough SNR of the injection for calibration
                    inj_snr = depth / (noise / np.sqrt(max(1, (dur / 24 / period) * n_points)))
                    cases.append({"depth": depth, "period": period, "duration_h": dur,
                                  "phase": phase, "recovered": bool(ok),
                                  "recovered_period": round(res.period, 4),
                                  "period_err_frac": round(err, 4),
                                  "injected_snr": round(float(inj_snr), 2),
                                  "measured_snr": round(res.snr, 2)})
    n = len(cases)
    return {"n_cases": n, "recovered": recovered,
            "recovery_rate": round(recovered / n, 3) if n else 0.0,
            "median_period_err_frac": round(float(np.median(period_errs)), 5)
            if period_errs else None,
            "cases": cases}


def recovery_vs_snr(*, snr_levels: list[float], period: float = 3.5, seed: int = 11,
                    n_points: int = 3000, trials: int = 10) -> dict[str, Any]:
    """Calibration: recovery fraction as a function of injected SNR."""
    rng = np.random.default_rng(seed)
    noise = 0.0017
    dur_h = 3.2
    curve = []
    for target_snr in snr_levels:
        # choose depth to hit target SNR given noise and #in-transit points
        n_in = max(1, int((dur_h / 24 / period) * n_points))
        depth = target_snr * noise / np.sqrt(n_in)
        hits = 0
        for _ in range(trials):
            time, base = _baseline(n_points, rng, noise=noise)
            inj = inject_box(time, base, period=period, depth=depth, duration_hours=dur_h)
            res = pl.pipeline_a(time, inj, window=51, p_min=0.5, p_max=8.0)
            if abs(res.period - period) / period < 0.01 and res.snr >= 7.0:
                hits += 1
        curve.append({"target_snr": target_snr, "depth": round(float(depth), 5),
                      "recovery_fraction": round(hits / trials, 2)})
    # monotonic, well-calibrated detector should recover ~none at low SNR, ~all at high
    return {"curve": curve,
            "low_snr_suppressed": curve[0]["recovery_fraction"] <= 0.3,
            "high_snr_recovered": curve[-1]["recovery_fraction"] >= 0.7}
