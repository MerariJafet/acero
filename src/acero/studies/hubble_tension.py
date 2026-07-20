"""Real-data analysis: the Hubble tension from public H0 measurements.

Loads a real compilation of H0 measurements (author/year/value/uncertainty/method/
category), computes inverse-variance weighted means for the early-universe (CMB) and
late-universe (distance-ladder / local) determinations, and quantifies the tension in
sigma. This describes an OPEN problem in cosmology about our cosmic context — it makes
NO discovery claim and does not resolve the tension.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from ..core.config import repo_root

EARLY = {"cmb_early_universe", "cmb_shf"}
LATE = {"distance_ladder", "pure_local", "local_lcdm"}


def _dataset() -> Path:
    return repo_root() / "research" / "datasets" / "hubble_tension_h0_measurements.csv"


def load_rows() -> list[dict[str, Any]]:
    out = []
    with _dataset().open() as f:
        for r in csv.DictReader(f):
            try:
                h0 = float(r["h0"])
                up = float(r["uncertainty_plus"])
                dn = float(r["uncertainty_minus"])
            except (TypeError, ValueError):
                continue
            sig = (up + dn) / 2 or up or dn
            if h0 > 0 and sig > 0:
                out.append({"author": r["author"], "year": int(r["year"]), "h0": h0,
                            "sigma": sig, "method": r["method"], "category": r["category"]})
    return out


def _weighted(group: list[dict[str, Any]]) -> tuple[float, float, int]:
    """Inverse-variance weighted mean and its uncertainty."""
    if not group:
        return (float("nan"), float("nan"), 0)
    w = [1.0 / (g["sigma"] ** 2) for g in group]
    mean = sum(wi * g["h0"] for wi, g in zip(w, group, strict=False)) / sum(w)
    err = math.sqrt(1.0 / sum(w))
    return (mean, err, len(group))


def analyze() -> dict[str, Any]:
    rows = load_rows()
    early = [r for r in rows if r["category"] in EARLY]
    late = [r for r in rows if r["category"] in LATE]
    e_mean, e_err, e_n = _weighted(early)
    l_mean, l_err, l_n = _weighted(late)

    diff = l_mean - e_mean
    comb = math.sqrt(e_err ** 2 + l_err ** 2)
    sigma = abs(diff) / comb if comb else float("nan")

    return {
        "ok": True, "source": "Public compilation of H0 measurements (2003–2025)",
        "n_measurements": len(rows), "n_methods": len({r["method"] for r in rows}),
        "early_universe": {"weighted_H0": round(e_mean, 2), "uncertainty": round(e_err, 2),
                           "n": e_n, "km_s_Mpc": True},
        "late_universe": {"weighted_H0": round(l_mean, 2), "uncertainty": round(l_err, 2),
                          "n": l_n, "km_s_Mpc": True},
        "difference_km_s_Mpc": round(diff, 2),
        "tension_sigma": round(sigma, 1),
        "significant_tension": sigma >= 3.0,
        "claim": (f"Con datos públicos reales, la determinación tardía/local de H0 "
                  f"({round(l_mean,1)}±{round(l_err,1)}) y la temprana/CMB "
                  f"({round(e_mean,1)}±{round(e_err,1)}) difieren ~{round(sigma,1)}σ: "
                  "la Tensión de Hubble. Es un problema ABIERTO; ACERO no lo resuelve "
                  "ni afirma su causa."),
        "cannot_conclude": [
            "la causa de la tensión (¿física nueva? ¿sistemáticos?) — no resuelta",
            "cuál valor de H0 es 'correcto' — no determinable desde esta compilación",
            "esta es una síntesis de mediciones publicadas, NO una medición nueva de ACERO",
        ],
        "prohibited_claims": ["resolver la tensión de Hubble", "descubrir nueva física",
                              "afirmar el valor verdadero de H0"],
    }
