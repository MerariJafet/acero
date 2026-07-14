"""Prediction-before-result.

Before revealing an important result, ACERO asks the human to predict it. The prediction
is LOCKED the moment a result is revealed: it cannot be edited afterwards (anti-HARKing
for the human). After the reveal we compare, identify which assumption failed, record the
learning, and detect overconfidence — but honest uncertainty is never punished.
"""

from __future__ import annotations

import re

from ..models import HumanPrediction


class PredictionLockedError(RuntimeError):
    """Raised on any attempt to modify a prediction after the result was revealed."""


def make_prediction(learner_id: str, project_id: str, experiment_id: str,
                    predicted_outcome: str, *, rationale: str = "",
                    confidence: float = 0.5) -> HumanPrediction:
    return HumanPrediction(
        learner_id=learner_id, research_project_id=project_id,
        experiment_id=experiment_id, predicted_outcome=predicted_outcome,
        rationale=rationale, confidence=max(0.0, min(1.0, confidence)))


def _similarity(a: str, b: str) -> float:
    ta = {w for w in re.split(r"\W+", a.lower()) if len(w) > 2}
    tb = {w for w in re.split(r"\W+", b.lower()) if len(w) > 2}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def reveal(pred: HumanPrediction, revealed_result: str, *,
           correct_tokens: list[str] | None = None) -> HumanPrediction:
    """Lock the prediction and compare it with the revealed result.

    Comparison is 'correct' if key result tokens appear in the prediction (or high token
    overlap), 'partial' if some overlap, else 'incorrect'.
    """
    if pred.locked:
        raise PredictionLockedError("prediction already revealed and locked")
    pred.revealed_result = revealed_result
    if correct_tokens:
        hit = sum(1 for t in correct_tokens
                  if t.lower() in pred.predicted_outcome.lower())
        frac = hit / len(correct_tokens)
        comp = "correct" if frac >= 0.75 else "partial" if frac > 0 else "incorrect"
    else:
        sim = _similarity(pred.predicted_outcome, revealed_result)
        comp = "correct" if sim >= 0.5 else "partial" if sim >= 0.2 else "incorrect"
    pred.comparison = comp
    pred.locked = True
    return pred


def edit_after_reveal(pred: HumanPrediction, _new_text: str) -> None:
    """Explicitly forbidden: editing a prediction after the result is known."""
    raise PredictionLockedError(
        "cannot edit a prediction after the result was revealed (anti-HARKing)")


def add_reflection(pred: HumanPrediction, reflection: str) -> HumanPrediction:
    """Reflection is allowed post-reveal; it does not alter the prediction itself."""
    pred.reflection = reflection
    return pred


def is_overconfident(pred: HumanPrediction, *, tol: float = 0.25) -> bool:
    """High stated confidence on a wrong prediction signals overconfidence."""
    return (pred.comparison == "incorrect" and pred.confidence >= 0.5 + tol)


def honest_uncertainty(pred: HumanPrediction) -> bool:
    """Low confidence on a wrong prediction is honest, not a failure to penalise."""
    return pred.comparison == "incorrect" and pred.confidence <= 0.4
