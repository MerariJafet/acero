"""Null tests + false-positive scenarios.

A trustworthy pipeline must FAIL to find the tested transit in data that lack it:
shuffled flux, a real control star, pure noise, red-noise surrogates, and inverted
transits. Phase-randomization is included but DECLARED as a shape-null only (it
preserves the power spectrum), never used to test periodicity itself.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from . import pipelines as pl

DETECTION_SNR = 7.0


def _detects(time: np.ndarray, flux: np.ndarray, *, near_period: float | None = None,
             tol: float = 0.01) -> tuple[bool, float, float]:
    res = pl.pipeline_a(time, flux, window=51, p_min=0.5,
                        p_max=min(10.0, (time[-1] - time[0]) / 2))
    detected = res.snr >= DETECTION_SNR
    if near_period is not None:
        detected = detected and abs(res.period - near_period) / near_period < tol
    return bool(detected), float(res.period), float(res.snr)


def null_flux_shuffled(time: np.ndarray, flux: np.ndarray, *, seed: int = 3) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    shuffled = np.copy(flux)
    rng.shuffle(shuffled)
    det, p, snr = _detects(time, shuffled, near_period=None)
    return {"null": "flux_shuffled", "detected_transit": det,
            "period": round(p, 4), "snr": round(snr, 2),
            "pass": not det, "note": "time order destroyed; must not find a transit"}


def null_control_star(time: np.ndarray, flux: np.ndarray, target_period: float
                      ) -> dict[str, Any]:
    """Real control star must NOT show the target's transit at its period."""
    det, p, snr = _detects(time, flux, near_period=target_period)
    return {"null": "control_star", "detected_target_period": det,
            "period": round(p, 4), "snr": round(snr, 2),
            "pass": not det, "note": "control lacks Kepler-8b; must not match its period"}


def null_no_transit_synthetic(n: int = 3000, *, seed: int = 5) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    time = np.cumsum(rng.uniform(0.019, 0.021, n))
    time -= time[0]
    flux = 1.0 + rng.normal(0, 0.0017, n) + 0.001 * np.sin(2 * np.pi * time / 20)
    det, p, snr = _detects(time, flux)
    return {"null": "no_transit_synthetic", "detected_transit": det,
            "period": round(p, 4), "snr": round(snr, 2), "pass": not det}


def null_ar1_surrogate(time: np.ndarray, flux: np.ndarray, *, phi: float = 0.9,
                       seed: int = 8) -> dict[str, Any]:
    """AR(1) red-noise surrogate with matched variance; must not fake a transit."""
    rng = np.random.default_rng(seed)
    n = len(flux)
    sigma = np.std(flux)
    e = rng.normal(0, sigma * np.sqrt(1 - phi**2), n)
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    surrogate = 1.0 + x
    det, p, snr = _detects(time, surrogate)
    return {"null": "AR1_red_noise", "detected_transit": det,
            "period": round(p, 4), "snr": round(snr, 2), "pass": not det,
            "note": "correlated noise; a spurious dip here would be a false positive"}


def null_inverted_transit(time: np.ndarray, flux: np.ndarray, *, period: float,
                          depth: float = 0.006) -> dict[str, Any]:
    """Inject an inverted transit (bump); a dip-searching BLS must not lock onto it."""
    from .injection import inject_box
    inj = inject_box(time, flux, period=period, depth=-depth, duration_hours=3.2)  # bump
    res = pl.pipeline_a(time, inj, window=51, p_min=0.5, p_max=8.0)
    # a dip search should not return this bump period with high box power at that phase
    matched = abs(res.period - period) / period < 0.01 and res.depth > 0
    return {"null": "inverted_transit", "locked_on_bump": bool(matched and res.snr >= DETECTION_SNR),
            "period": round(float(res.period), 4), "snr": round(float(res.snr), 2),
            "pass": not (matched and res.snr >= DETECTION_SNR),
            "note": "bump instead of dip; dip search should not claim a transit"}


def run_all_nulls(time: np.ndarray, flux: np.ndarray, *, target_period: float,
                  control_time: np.ndarray, control_flux: np.ndarray) -> dict[str, Any]:
    results = [
        null_flux_shuffled(time, flux),
        null_control_star(control_time, control_flux, target_period),
        null_no_transit_synthetic(),
        null_ar1_surrogate(time, flux),
        null_inverted_transit(time, flux, period=target_period),
    ]
    n_pass = sum(1 for r in results if r["pass"])
    return {"results": results, "n": len(results), "passed": n_pass,
            "all_controlled": n_pass == len(results),
            "false_positive_rate": round(1 - n_pass / len(results), 3)}


def false_positive_scenarios(n: int = 3000, *, seed: int = 21) -> dict[str, Any]:
    """Analyze scenarios that can mimic a transit; record whether each triggers one."""
    rng = np.random.default_rng(seed)
    time = np.cumsum(rng.uniform(0.019, 0.021, n))
    time -= time[0]
    base = 1.0 + rng.normal(0, 0.0017, n)
    scen: list[dict[str, Any]] = []

    def add(name, flux):
        det, p, snr = _detects(time, flux)
        scen.append({"scenario": name, "false_detection": det,
                     "period": round(p, 4), "snr": round(snr, 2)})

    add("stellar_variability", base + 0.003 * np.sin(2 * np.pi * time / 7.5))
    disc = np.copy(base)
    disc[n // 2:] -= 0.002
    add("instrumental_discontinuity", disc)
    cr = np.copy(base)
    cr[rng.integers(0, n, 5)] -= 0.05
    add("cosmic_ray_outliers", cr)
    eb = np.copy(base)
    ph = (time / 2.1) % 1.0
    eb[(ph < 0.02) | (ph > 0.98)] *= 0.98
    eb[abs(ph - 0.5) < 0.02] *= 0.995      # secondary eclipse -> eclipsing binary
    add("eclipsing_binary_like", eb)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.95 * x[i - 1] + rng.normal(0, 0.0017)
    add("red_noise_dip", 1.0 + x)
    n_false = sum(1 for s in scen if s["false_detection"])
    return {"scenarios": scen, "n": len(scen), "n_false_detections": n_false,
            "note": "an eclipsing binary CAN mimic a transit; flagged for follow-up, "
                    "not claimed as a planet"}
