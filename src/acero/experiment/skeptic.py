"""The Skeptic: a rule-based adversarial reviewer (Sprint 4 minimal version).

It does not certify correctness. It raises the standard scientific objections a
reviewer would, and — where possible — checks them against the recorded run so
the challenge is grounded, not decorative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Objection:
    concern: str
    question: str
    automated_check: str = "not_checked"  # passed | failed | not_checked
    detail: str = ""


@dataclass
class SkepticReview:
    objections: list[Objection] = field(default_factory=list)

    @property
    def unresolved(self) -> list[Objection]:
        return [o for o in self.objections if o.automated_check == "failed"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "objections": [o.__dict__ for o in self.objections],
            "n_objections": len(self.objections),
            "n_failed_checks": len(self.unresolved),
        }


def review_experiment(prereg: dict[str, Any], run_record: dict[str, Any],
                      metrics: dict[str, Any]) -> SkepticReview:
    """Produce grounded objections about a computational experiment."""
    objections: list[Objection] = []

    # Data leakage: are train/test disjoint?
    leakage = metrics.get("train_test_disjoint")
    objections.append(Objection(
        concern="data_leakage",
        question="Are training and test sets disjoint (no leakage)?",
        automated_check="passed" if leakage else ("failed" if leakage is False else "not_checked"),
        detail=f"train_test_disjoint={leakage}",
    ))

    # Overfitting: does test error blow up vs train?
    train_err = metrics.get("train_rmse")
    test_err = metrics.get("test_rmse")
    if train_err is not None and test_err is not None:
        ratio = test_err / train_err if train_err else float("inf")
        objections.append(Objection(
            concern="overfitting",
            question="Does the model generalise, or is test error >> train error?",
            automated_check="failed" if ratio > 3.0 else "passed",
            detail=f"test/train RMSE ratio={ratio:.2f}",
        ))

    # Extrapolation: was the model tested outside the training range?
    extra_err = metrics.get("extrapolation_rmse")
    objections.append(Objection(
        concern="limited_range",
        question="Was the model tested OUTSIDE the training range (extrapolation)?",
        automated_check="passed" if extra_err is not None else "not_checked",
        detail=f"extrapolation_rmse={extra_err}",
    ))

    # Baseline: is there a naive baseline to beat?
    objections.append(Objection(
        concern="baseline",
        question="Is a naive baseline reported, and does the model beat it?",
        automated_check="passed" if metrics.get("baseline_rmse") is not None else "failed",
        detail=f"baseline_rmse={metrics.get('baseline_rmse')}",
    ))

    # Metric selection / multiple seeds.
    seeds = run_record.get("seeds", [])
    objections.append(Objection(
        concern="seed_sensitivity",
        question="Were multiple random seeds used to check stability?",
        automated_check="passed" if len(seeds) >= 2 else "failed",
        detail=f"n_seeds={len(seeds)}",
    ))

    # The deep objection: fit != causal explanation.
    objections.append(Objection(
        concern="fit_is_not_explanation",
        question="Does recovering a functional form constitute a causal/physical explanation?",
        automated_check="not_checked",
        detail="Recovering a known law from synthetic data is NOT new knowledge.",
    ))

    return SkepticReview(objections=objections)
