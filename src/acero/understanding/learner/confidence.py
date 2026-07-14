"""Human confidence calibration.

Reuses the inference-engine calibration primitives (Brier score, reliability) to judge
whether the researcher's *self-reported* confidence matches their *observed* performance.
Honest uncertainty is never punished; systematic overconfidence is surfaced.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...inference.calibration.calibration import calibrate


@dataclass
class HumanCalibration:
    n: int
    brier: float
    calibration_error: float
    mean_confidence: float
    mean_correct: float
    tendency: str            # overconfident | underconfident | calibrated | insufficient

    def as_dict(self) -> dict[str, float | int | str]:
        return {"n": self.n, "brier": self.brier,
                "calibration_error": self.calibration_error,
                "mean_confidence": self.mean_confidence,
                "mean_correct": self.mean_correct, "tendency": self.tendency}


def assess(confidences: list[float], correct: list[bool], *, min_n: int = 4,
           tol: float = 0.1) -> HumanCalibration:
    """Compare stated confidences with realised correctness."""
    n = len(confidences)
    if n < min_n or n != len(correct):
        return HumanCalibration(n, 0.0, 0.0, 0.0, 0.0, "insufficient")
    rep = calibrate(confidences, correct)
    mc = sum(confidences) / n
    ma = sum(1.0 if c else 0.0 for c in correct) / n
    gap = mc - ma
    if gap > tol:
        tendency = "overconfident"
    elif gap < -tol:
        tendency = "underconfident"
    else:
        tendency = "calibrated"
    return HumanCalibration(n, round(rep.brier_score, 4),
                            round(rep.calibration_error, 4),
                            round(mc, 4), round(ma, 4), tendency)
