"""Standalone transit analysis — THREE methods, no ACERO imports.

Method A: median detrend + astropy BoxLeastSquares (box statistic).
Method B: polynomial detrend + Phase Dispersion Minimization (PDM).
Method C (ALTERNATIVE IMPLEMENTATION): a from-scratch box matched-filter period
         search using only numpy — a DIFFERENT method and DIFFERENT code path for
         the same question and data. Shared dependency: numpy (recorded).

Recovering the KNOWN Kepler-8b transit is not a discovery.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.timeseries import BoxLeastSquares

KNOWN_PERIOD = 3.52254


def read_series(data_dir: Path, kic: str, quarters: list[str]) -> tuple[np.ndarray, np.ndarray]:
    t: list[float] = []
    f: list[float] = []
    for q in quarters:
        with fits.open(data_dir / f"kplr{kic}-{q}_llc.fits") as hdul:
            d = hdul[1].data
            for tt, ff, qual in zip(d["TIME"], d["PDCSAP_FLUX"], d["SAP_QUALITY"], strict=False):
                if int(qual) != 0 or math.isnan(float(tt)) or math.isnan(float(ff)):
                    continue
                t.append(float(tt))
                f.append(float(ff))
    arr = np.array(f)
    return np.array(t), arr / np.median(arr)


def _median_detrend(flux: np.ndarray, half: int = 50) -> np.ndarray:
    n = len(flux)
    trend = np.array([np.median(flux[max(0, i - half):min(n, i + half + 1)]) for i in range(n)])
    trend[trend == 0] = 1.0
    return flux / trend


def _poly_detrend(time: np.ndarray, flux: np.ndarray, seg_days: float = 5.0,
                  order: int = 2) -> np.ndarray:
    out = np.copy(flux)
    seg = ((time - time[0]) // seg_days).astype(int)
    for s in np.unique(seg):
        m = seg == s
        if m.sum() < order + 2:
            continue
        c = np.polyfit(time[m] - time[m].mean(), flux[m], order)
        tr = np.polyval(c, time[m] - time[m].mean())
        tr[tr == 0] = 1.0
        out[m] = flux[m] / tr
    return out


def method_a_bls(time: np.ndarray, flux: np.ndarray) -> float:
    det = _median_detrend(flux)
    model = BoxLeastSquares(time, det)
    periods = np.linspace(0.5, 8.0, 4000)
    res = model.power(periods, [0.05, 0.1, 0.15, 0.2])
    return float(res.period[int(np.argmax(res.power))])


def method_b_pdm(time: np.ndarray, flux: np.ndarray, nbins: int = 20) -> float:
    det = _poly_detrend(time, flux)
    total_var = np.var(det)
    periods = np.linspace(0.5, 8.0, 4000)
    best_p, best_theta = periods[0], 1e9
    for p in periods:
        phase = ((time - time[0]) / p) % 1.0
        idx = np.clip((phase * nbins).astype(int), 0, nbins - 1)
        num = den = 0.0
        for b in range(nbins):
            y = det[idx == b]
            if len(y) > 1:
                num += (len(y) - 1) * np.var(y)
                den += (len(y) - 1)
        theta = (num / den) / total_var if den and total_var else 1.0
        if theta < best_theta:
            best_theta, best_p = theta, p
    return float(best_p)


def method_c_matched_box(time: np.ndarray, flux: np.ndarray) -> float:
    """ALTERNATIVE: numpy-only box matched-filter over a period/phase grid."""
    det = _median_detrend(flux)
    resid = det - np.mean(det)
    periods = np.linspace(0.5, 8.0, 2500)
    dur_frac = 0.04
    best_p, best_stat = periods[0], -1e9
    for p in periods:
        phase = ((time - time[0]) / p) % 1.0
        # correlate a negative box (dip) centered at the best phase
        nb = 25
        binned = np.array([resid[(phase >= b / nb) & (phase < (b + 1) / nb)].mean()
                           if np.any((phase >= b / nb) & (phase < (b + 1) / nb)) else 0.0
                           for b in range(nb)])
        depth = -binned.min()                 # deepest bin
        width = max(1, int(dur_frac * nb))
        stat = depth * math.sqrt(width)       # crude matched-filter score
        if stat > best_stat:
            best_stat, best_p = stat, p
    return float(best_p)


def analyze(data_dir: Path) -> dict[str, object]:
    t, f = read_series(data_dir, "006922244",
                       ["2009259160929", "2009350155506", "2010078095331"])
    a = method_a_bls(t, f)
    b = method_b_pdm(t, f)
    c = method_c_matched_box(t, f)
    def err(p: float) -> float:
        return abs(p - KNOWN_PERIOD) / KNOWN_PERIOD
    return {
        "n_points": len(t),
        "method_A_BLS": round(a, 5), "method_B_PDM": round(b, 5),
        "method_C_matched_box": round(c, 5),
        "frac_err_A": round(err(a), 5), "frac_err_B": round(err(b), 5),
        "frac_err_C": round(err(c), 5),
        "all_recover_known": err(a) < 0.005 and err(b) < 0.005 and err(c) < 0.02,
        "shared_dependencies": ["numpy", "astropy(io.fits) for A/B; C is numpy-only"],
        "is_discovery": False,
    }
