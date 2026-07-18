"""Two competing transit-search pipelines over the SAME data.

Pipeline A: median detrend + Box Least Squares (box statistic, astropy).
Pipeline B: polynomial-segment detrend + Phase Dispersion Minimization (PDM).

They use different detrending AND different period statistics, so agreement is
informative — but they share the SAME light curve, so they are NOT independent
replication (declared in the preregistration and enforced in the abstention rules).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

# --- detrending ------------------------------------------------------------

def detrend_median(flux: np.ndarray, window: int = 101) -> np.ndarray:
    """Sliding-median normalization (robust to outliers); Pipeline A."""
    if window % 2 == 0:
        window += 1
    n = len(flux)
    half = window // 2
    trend = np.empty(n)
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        trend[i] = np.median(flux[lo:hi])
    trend[trend == 0] = 1.0
    return flux / trend


def detrend_poly(time: np.ndarray, flux: np.ndarray, segment_days: float = 5.0,
                 order: int = 2) -> np.ndarray:
    """Per-segment low-order polynomial detrend; Pipeline B (different basis)."""
    out = np.copy(flux)
    if len(time) == 0:
        return out
    t0 = time[0]
    seg = ((time - t0) // segment_days).astype(int)
    for s in np.unique(seg):
        mask = seg == s
        if mask.sum() < order + 2:
            continue
        t = time[mask]
        coeffs = np.polyfit(t - t.mean(), flux[mask], order)
        trend = np.polyval(coeffs, t - t.mean())
        trend[trend == 0] = 1.0
        out[mask] = flux[mask] / trend
    return out


# --- results ---------------------------------------------------------------

@dataclass
class SearchResult:
    pipeline: str
    period: float
    depth: float
    duration: float
    snr: float
    power: float
    t0: float

    def as_dict(self) -> dict[str, Any]:
        return {"pipeline": self.pipeline, "period": round(self.period, 6),
                "depth": round(self.depth, 6), "duration": round(self.duration, 5),
                "snr": round(self.snr, 3), "power": round(self.power, 5),
                "t0": round(self.t0, 5)}


# --- Pipeline A: BLS -------------------------------------------------------

def pipeline_a(time: np.ndarray, flux: np.ndarray, *, window: int = 101,
               p_min: float = 0.5, p_max: float = 10.0,
               durations: tuple[float, ...] = (0.05, 0.1, 0.15, 0.2)) -> SearchResult:
    from astropy.timeseries import BoxLeastSquares

    det = detrend_median(flux, window)
    model = BoxLeastSquares(time, det)
    periods = np.linspace(p_min, p_max, 4000)
    res = model.power(periods, list(durations))
    i = int(np.argmax(res.power))
    period = float(res.period[i])
    depth = float(res.depth[i])
    duration = float(res.duration[i])
    power = float(res.power[i])
    # SNR: depth over the robust scatter of the detrended residuals per point-in-transit
    resid_std = float(np.std(det))
    n_in = max(1, int(duration / np.median(np.diff(time)) * (time[-1] - time[0]) / period))
    snr = depth / (resid_std / np.sqrt(n_in)) if resid_std > 0 else 0.0
    t0 = float(res.transit_time[i])
    return SearchResult("A_BLS", period, depth, duration, snr, power, t0)


# --- Pipeline B: PDM -------------------------------------------------------

def _pdm_theta(phase: np.ndarray, y: np.ndarray, nbins: int = 20) -> float:
    """Phase Dispersion Minimization statistic: binned variance / total variance."""
    total_var = np.var(y)
    if total_var == 0:
        return 1.0
    bins = np.linspace(0, 1, nbins + 1)
    idx = np.digitize(phase, bins) - 1
    num = 0.0
    den = 0.0
    for b in range(nbins):
        m = idx == b
        cnt = int(m.sum())
        if cnt > 1:
            num += (cnt - 1) * np.var(y[m])
            den += (cnt - 1)
    if den == 0:
        return 1.0
    return float((num / den) / total_var)


def pipeline_b(time: np.ndarray, flux: np.ndarray, *, order: int = 2,
               p_min: float = 0.5, p_max: float = 10.0) -> SearchResult:
    det = detrend_poly(time, flux, order=order)
    periods = np.linspace(p_min, p_max, 4000)
    thetas = np.empty(len(periods))
    for k, p in enumerate(periods):
        phase = ((time - time[0]) / p) % 1.0
        thetas[k] = _pdm_theta(phase, det)
    i = int(np.argmin(thetas))
    period = float(periods[i])
    theta = float(thetas[i])
    # transit metrics at the recovered period: fold and take the deepest bin
    phase = ((time - time[0]) / period) % 1.0
    nbins = 40
    binned = np.array([det[(phase >= b / nbins) & (phase < (b + 1) / nbins)].mean()
                       if np.any((phase >= b / nbins) & (phase < (b + 1) / nbins)) else 1.0
                       for b in range(nbins)])
    depth = float(1.0 - np.min(binned))
    duration = float((np.sum(binned < (1.0 - depth / 2)) / nbins) * period)
    resid_std = float(np.std(det))
    snr = depth / (resid_std / np.sqrt(len(det) / nbins)) if resid_std > 0 else 0.0
    power = float(1.0 - theta)                      # higher = stronger phase coherence
    t0 = float(time[0] + np.argmin(binned) / nbins * period)
    return SearchResult("B_PDM", period, depth, duration, snr, power, t0)


def period_agreement(a: SearchResult, b: SearchResult) -> dict[str, Any]:
    """Compare recovered periods; also test 1x / 2x / 0.5x aliases."""
    ratios = {"1x": b.period, "2x": b.period / 2, "0.5x": b.period * 2}
    best = min(ratios.items(), key=lambda kv: abs(a.period - kv[1]))
    frac = abs(a.period - best[1]) / a.period if a.period else 1.0
    return {"a_period": round(a.period, 5), "b_period": round(b.period, 5),
            "best_alias": best[0], "frac_diff": round(frac, 5),
            "agree_1pct": frac < 0.01}
