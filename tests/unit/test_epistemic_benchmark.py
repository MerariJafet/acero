"""EP5: EVA vulnerability benchmark — recall + specificity (offline)."""

from __future__ import annotations

from acero.epistemic.vulnerability_benchmark import build_cases, evaluate


def test_cases_include_flawed_and_strong():
    cases = build_cases()
    assert any(c.expected is None for c in cases)      # a strong claim
    assert sum(1 for c in cases if c.expected) >= 5    # several flawed


def test_eva_recalls_known_flaws():
    rep = evaluate()
    assert rep.recall >= 0.8            # finds most known vulnerabilities


def test_eva_does_not_over_flag_strong_claim():
    rep = evaluate()
    # a strong claim (independent replication + boundaries + mechanism + experimental)
    # should not raise high-severity flags
    assert rep.false_flags_on_strong == 0


def test_report_labels_itself_preliminary():
    assert "preliminar" in str(evaluate().summary()["estatus"])
