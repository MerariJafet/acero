"""F10+F11: question benchmark with dev/calib/eval splits + metrics (offline)."""

from __future__ import annotations

from acero.epistemic.question_benchmark import Split, build_cases, evaluate


def test_splits_are_separated():
    cases = build_cases()
    splits = {c.split for c in cases}
    assert splits == {Split.DEVELOPMENT, Split.CALIBRATION, Split.EVALUATION}
    # evaluation must contain the strong claim + an unanswerable case
    ev = [c for c in cases if c.split == Split.EVALUATION]
    assert any(c.expected_vuln is None for c in ev)


def test_metrics_computed_on_eval_split_only():
    rep = evaluate()
    # eval split has several flawed cases + strong + unanswerable
    assert rep.n_eval >= 5
    assert rep.vulnerability_recall >= 0.75
    assert rep.useful_question_rate >= 0.5


def test_strong_claim_not_over_flagged():
    rep = evaluate()
    assert rep.false_flags_on_strong == 0


def test_report_labeled_preliminary_with_splits():
    s = evaluate().summary()
    assert "preliminar" in str(s["estatus"]) and "splits" in str(s["estatus"])
