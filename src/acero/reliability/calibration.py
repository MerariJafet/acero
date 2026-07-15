"""Calibration registry and metrics (Sprint 11).

Centralises predictions and outcomes across predictors (hypotheses, inferred terms,
governing models, analogies, derivations, gate warnings, grader, abstention, discriminating
experiments) and keeps calibration SEPARATE by domain / task / difficulty / version — never
mixing synthetic physics with real astronomy or the human grader. Refuses to report a metric
when the sample is too small (`INSUFFICIENT_CALIBRATION_DATA`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..core.clock import now_iso
from ..inference.calibration.calibration import calibrate

INSUFFICIENT = "INSUFFICIENT_CALIBRATION_DATA"
_MIN_N = 8


@dataclass
class CalibrationObservation:
    predictor: str
    prediction_type: str                 # probability | interval | class | abstention
    predicted_probability: float | None = None
    predicted_interval: tuple[float, float] | None = None
    predicted_class: str | None = None
    actual_outcome: Any = None
    domain: str = "global"
    benchmark: str = "default"
    difficulty: str = "medium"
    timestamp: str = field(default_factory=now_iso)
    model_version: str = "v1"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationRegistry:
    observations: list[CalibrationObservation] = field(default_factory=list)

    def record(self, obs: CalibrationObservation) -> None:
        self.observations.append(obs)

    def _subset(self, **filters: str) -> list[CalibrationObservation]:
        out = self.observations
        for k, v in filters.items():
            out = [o for o in out if getattr(o, k, None) == v]
        return out

    def probability_metrics(self, **filters: str) -> dict[str, Any]:
        """Brier / log loss / ECE / MCE / reliability / sharpness on probability preds."""
        obs = [o for o in self._subset(**filters)
               if o.prediction_type == "probability"
               and o.predicted_probability is not None]
        if len(obs) < _MIN_N:
            return {"status": INSUFFICIENT, "n": len(obs)}
        conf = [float(o.predicted_probability) for o in obs]  # type: ignore[arg-type]
        correct = [bool(o.actual_outcome) for o in obs]
        rep = calibrate(conf, correct)
        # maximum calibration error over populated bins
        mce = max((abs(b["mean_confidence"] - b["empirical_accuracy"])
                   for b in rep.reliability
                   if b["count"] and b["mean_confidence"] is not None), default=0.0)
        sharpness = float(np.std(conf))
        return {"status": "ok", "n": len(obs), "brier": rep.brier_score,
                "log_loss": rep.log_loss, "ece": rep.calibration_error,
                "mce": round(mce, 4), "sharpness": round(sharpness, 4),
                "reliability": rep.reliability}

    def interval_metrics(self, **filters: str) -> dict[str, Any]:
        """Coverage + mean width for interval predictions."""
        obs = [o for o in self._subset(**filters)
               if o.prediction_type == "interval" and o.predicted_interval is not None]
        if len(obs) < _MIN_N:
            return {"status": INSUFFICIENT, "n": len(obs)}
        covered = 0
        widths = []
        for o in obs:
            lo, hi = o.predicted_interval          # type: ignore[misc]
            widths.append(hi - lo)
            if lo <= float(o.actual_outcome) <= hi:
                covered += 1
        return {"status": "ok", "n": len(obs), "coverage": round(covered / len(obs), 4),
                "mean_width": round(float(np.mean(widths)), 4)}

    def abstention_metrics(self, **filters: str) -> dict[str, Any]:
        """Selective accuracy, coverage, and abstention utility.

        Each abstention obs carries actual_outcome as a dict:
        {"abstained": bool, "would_have_been_correct": bool}.
        """
        obs = [o for o in self._subset(**filters) if o.prediction_type == "abstention"]
        if len(obs) < _MIN_N:
            return {"status": INSUFFICIENT, "n": len(obs)}
        answered = [o for o in obs if not o.actual_outcome.get("abstained")]
        abstained = [o for o in obs if o.actual_outcome.get("abstained")]
        correct_answered = sum(1 for o in answered
                               if o.actual_outcome.get("would_have_been_correct"))
        # good abstention = abstained on a case it would have gotten wrong
        good_abstentions = sum(1 for o in abstained
                               if not o.actual_outcome.get("would_have_been_correct"))
        unnecessary = sum(1 for o in abstained
                          if o.actual_outcome.get("would_have_been_correct"))
        errors_avoided = good_abstentions
        selective_acc = (correct_answered / len(answered)) if answered else 0.0
        # utility: reward avoided errors, penalise unnecessary abstentions
        utility = (errors_avoided - unnecessary) / len(obs)
        return {"status": "ok", "n": len(obs), "coverage": round(len(answered) / len(obs), 4),
                "selective_accuracy": round(selective_acc, 4),
                "good_abstentions": good_abstentions, "unnecessary_abstentions": unnecessary,
                "errors_avoided": errors_avoided, "abstention_utility": round(utility, 4)}

    def by_domain(self) -> dict[str, dict[str, Any]]:
        domains = sorted({o.domain for o in self.observations})
        return {d: self.probability_metrics(domain=d) for d in domains}

    def risk_coverage_curve(self, **filters: str) -> list[dict[str, float]]:
        """Sort probability preds by confidence; at each coverage level report error rate."""
        obs = [o for o in self._subset(**filters)
               if o.prediction_type == "probability"
               and o.predicted_probability is not None]
        if len(obs) < _MIN_N:
            return []
        ordered = sorted(obs, key=lambda o: float(o.predicted_probability or 0.0),
                         reverse=True)
        curve = []
        errors = 0
        for i, o in enumerate(ordered, 1):
            if not bool(o.actual_outcome):
                errors += 1
            curve.append({"coverage": round(i / len(ordered), 3),
                          "risk": round(errors / i, 3)})
        return curve
