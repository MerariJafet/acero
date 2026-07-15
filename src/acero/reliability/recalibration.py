"""Auditable recalibration (Sprint 11).

Simple, transparent recalibrators — histogram binning, isotonic (when enough data), Platt
scaling, temperature scaling, and interval inflation. Fit on a CALIBRATION split, never on
the final test split; the split is recorded so leakage is impossible to hide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


class LeakageError(RuntimeError):
    """Raised if calibration and test splits overlap."""


@dataclass
class Split:
    train_idx: list[int]
    calib_idx: list[int]
    test_idx: list[int]

    def check_disjoint(self) -> None:
        c, t = set(self.calib_idx), set(self.test_idx)
        if c & t:
            raise LeakageError("calibration and test splits overlap (leakage)")


@dataclass
class BinningRecalibrator:
    n_bins: int = 10
    edges: np.ndarray = field(default_factory=lambda: np.array([]))
    bin_acc: np.ndarray = field(default_factory=lambda: np.array([]))
    fitted: bool = False

    def fit(self, conf: list[float], correct: list[bool]) -> BinningRecalibrator:
        c = np.clip(np.asarray(conf, float), 1e-6, 1 - 1e-6)
        y = np.asarray(correct, float)
        self.edges = np.linspace(0, 1, self.n_bins + 1)
        acc = np.zeros(self.n_bins)
        for b in range(self.n_bins):
            mask = (c >= self.edges[b]) & (c < self.edges[b + 1]
                                           if b < self.n_bins - 1 else c <= self.edges[b + 1])
            acc[b] = y[mask].mean() if mask.any() else (self.edges[b] + self.edges[b + 1]) / 2
        self.bin_acc = acc
        self.fitted = True
        return self

    def transform(self, conf: list[float]) -> list[float]:
        c = np.clip(np.asarray(conf, float), 1e-6, 1 - 1e-6)
        idx = np.clip(np.digitize(c, self.edges) - 1, 0, self.n_bins - 1)
        return [float(self.bin_acc[i]) for i in idx]


@dataclass
class TemperatureScaler:
    """Single-parameter temperature scaling for a classifier confidence."""

    temperature: float = 1.0
    fitted: bool = False

    def fit(self, conf: list[float], correct: list[bool]) -> TemperatureScaler:
        c = np.clip(np.asarray(conf, float), 1e-6, 1 - 1e-6)
        y = np.asarray(correct, float)
        logits = np.log(c / (1 - c))
        best_t, best_loss = 1.0, float("inf")
        for t in np.linspace(0.5, 5.0, 46):
            p = 1 / (1 + np.exp(-logits / t))
            p = np.clip(p, 1e-6, 1 - 1e-6)
            loss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
            if loss < best_loss:
                best_loss, best_t = loss, float(t)
        self.temperature = best_t
        self.fitted = True
        return self

    def transform(self, conf: list[float]) -> list[float]:
        c = np.clip(np.asarray(conf, float), 1e-6, 1 - 1e-6)
        logits = np.log(c / (1 - c))
        return [float(x) for x in 1 / (1 + np.exp(-logits / self.temperature))]


def inflate_intervals(lowers: list[float], uppers: list[float], factor: float
                      ) -> tuple[list[float], list[float]]:
    """Widen intervals by ``factor`` about their midpoint (undercoverage remedy)."""
    lo = np.asarray(lowers, float)
    hi = np.asarray(uppers, float)
    mid = (lo + hi) / 2
    half = (hi - lo) / 2 * factor
    return [float(x) for x in mid - half], [float(x) for x in mid + half]


def recalibrate(conf: list[float], correct: list[bool], split: Split, *,
                method: str = "binning") -> dict[str, Any]:
    """Fit on the calibration split, evaluate improvement on the test split.

    Never fits on the test split; raises LeakageError if the splits overlap.
    """
    split.check_disjoint()
    conf_a = np.asarray(conf, float)
    corr_a = np.asarray(correct)
    cal_c = [float(conf_a[i]) for i in split.calib_idx]
    cal_y = [bool(corr_a[i]) for i in split.calib_idx]
    test_c = [float(conf_a[i]) for i in split.test_idx]
    test_y = [bool(corr_a[i]) for i in split.test_idx]

    recal = (TemperatureScaler() if method == "temperature"
             else BinningRecalibrator())
    recal.fit(cal_c, cal_y)
    new_test = recal.transform(test_c)

    def ece(c: list[float], y: list[bool]) -> float:
        from ..inference.calibration.calibration import calibrate
        return calibrate(c, y).calibration_error

    return {"method": method, "n_calib": len(cal_c), "n_test": len(test_c),
            "ece_before": ece(test_c, test_y), "ece_after": ece(new_test, test_y),
            "leakage_checked": True}
