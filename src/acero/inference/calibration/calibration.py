"""Calibration (Sprint 8.9).

Empirical calibration of confidence scores against known-truth benchmarks:
reliability diagram, Brier score, log loss, and interval coverage. Distinguishes a
heuristic score from an empirical frequency, a posterior probability, an uncertainty
interval, and LLM confidence — these are NEVER mixed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class CalibrationResult:
    brier_score: float
    log_loss: float
    calibration_error: float           # mean |confidence - empirical accuracy| over bins
    reliability: list[dict[str, Any]] = field(default_factory=list)
    n: int = 0
    kind: str = "heuristic_score_vs_empirical_frequency"


def calibrate(confidences: list[float], correct: list[bool], *, n_bins: int = 10
              ) -> CalibrationResult:
    """confidences[i] in [0,1] is the score assigned; correct[i] is ground truth."""
    conf = np.clip(np.asarray(confidences, dtype=float), 1e-6, 1 - 1e-6)
    y = np.asarray(correct, dtype=float)
    if len(conf) == 0:
        return CalibrationResult(0.0, 0.0, 0.0, [], 0)
    brier = float(np.mean((conf - y) ** 2))
    logloss = float(-np.mean(y * np.log(conf) + (1 - y) * np.log(1 - conf)))

    bins = np.linspace(0, 1, n_bins + 1)
    reliability = []
    cal_err = 0.0
    total = 0
    for b in range(n_bins):
        mask = (conf >= bins[b]) & (conf < bins[b + 1] if b < n_bins - 1 else conf <= bins[b + 1])
        cnt = int(mask.sum())
        if cnt == 0:
            reliability.append({"bin": [round(bins[b], 2), round(bins[b + 1], 2)],
                                "count": 0, "mean_confidence": None, "empirical_accuracy": None})
            continue
        mc = float(conf[mask].mean())
        acc = float(y[mask].mean())
        reliability.append({"bin": [round(bins[b], 2), round(bins[b + 1], 2)], "count": cnt,
                            "mean_confidence": round(mc, 4), "empirical_accuracy": round(acc, 4)})
        cal_err += cnt * abs(mc - acc)
        total += cnt
    cal_err = cal_err / total if total else 0.0
    return CalibrationResult(round(brier, 4), round(logloss, 4), round(cal_err, 4),
                             reliability, len(conf))


def interval_coverage(predictions: list[float], lowers: list[float], uppers: list[float],
                      truths: list[float]) -> dict[str, Any]:
    """Fraction of truths falling inside their predicted intervals (should ≈ nominal)."""
    lo = np.asarray(lowers)
    hi = np.asarray(uppers)
    t = np.asarray(truths)
    inside = float(np.mean((t >= lo) & (t <= hi))) if len(t) else 0.0
    return {"coverage": round(inside, 4), "n": len(t),
            "mean_interval_width": round(float(np.mean(hi - lo)), 4) if len(t) else 0.0}


def bootstrap_confidence(values: list[float], *, n_boot: int = 500, seed: int = 0
                         ) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"mean": 0.0, "lo95": 0.0, "hi95": 0.0}
    means = [float(np.mean(rng.choice(arr, size=len(arr), replace=True))) for _ in range(n_boot)]
    return {"mean": round(float(np.mean(arr)), 4),
            "lo95": round(float(np.percentile(means, 2.5)), 4),
            "hi95": round(float(np.percentile(means, 97.5)), 4)}


# Explicit distinction so callers never mix confidence kinds.
CONFIDENCE_KINDS = ("heuristic_score", "empirical_frequency", "posterior_probability",
                    "uncertainty_interval", "llm_confidence")
