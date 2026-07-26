"""P1: pipeline-level recovery scoring — a null control must never grade as a false
positive; a positive must be recovered."""
from __future__ import annotations

from acero.portal.recovery_bench import CONTROL_SET, derive_outcome, grade


def _exps(*verdicts):
    return [{"synthetic": False, "result": {"verdict": v}} for v in verdicts]


def test_control_set_has_positives_and_nulls():
    exp = {c["expected"] for c in CONTROL_SET}
    assert exp == {"positive", "null"}
    assert sum(c["expected"] == "null" for c in CONTROL_SET) >= 3


def test_derive_outcome_labels():
    assert derive_outcome(_exps("supports", "supports", "supports")) == "positive_robust"
    assert derive_outcome(_exps("refutes", "refutes")) == "refuted"
    assert derive_outcome(_exps("supports", "refutes", "inconclusive")) == "inconclusive"
    assert derive_outcome(_exps("inconclusive")) == "inconclusive"
    assert derive_outcome([]) == "no_evidence"
    # synthetic-only must not count as evidence
    assert derive_outcome([{"synthetic": True, "result": {"verdict": "supports"}}]) == "no_evidence"


def test_grade_positive_and_null():
    assert grade("positive", "positive_robust")["correct"] is True
    assert grade("positive", "inconclusive")["correct"] is False
    # the dangerous case: a null control coming back positive
    g = grade("null", "positive_robust")
    assert g["correct"] is False and "FALSO POSITIVO" in g["fail_mode"]
    assert grade("null", "inconclusive")["correct"] is True
