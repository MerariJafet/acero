"""Self-calibration guardrails: auto-tuning may raise sensitivity but NEVER trade away
specificity (a false positive on a null control forces a rollback)."""
from __future__ import annotations

from acero.portal.calibration import BOUNDS, DEFAULTS, Calibration
from acero.portal.recovery_bench import summarize


def _cal(tmp_path):
    return Calibration(path=tmp_path / "cal.json")


def test_defaults_and_persistence(tmp_path):
    c = _cal(tmp_path)
    assert c.get("astronomy")["cross_check_rel_tol"] == DEFAULTS["cross_check_rel_tol"]
    c.record_benchmark("astronomy", {"positives_total": 3, "positives_correct": 1,
                                     "nulls_total": 3, "nulls_correct": 3,
                                     "false_positives": 0, "accuracy": 0.66})
    # reload from disk → persisted
    assert Calibration(path=tmp_path / "cal.json").retro("astronomy")["runs"] == 1


def test_loosens_when_specificity_perfect_but_sensitivity_low(tmp_path):
    c = _cal(tmp_path)
    before = c.get("astronomy")["cross_check_rel_tol"]
    c.record_benchmark("astronomy", {"positives_total": 3, "positives_correct": 1,
                                     "nulls_total": 3, "nulls_correct": 3,
                                     "false_positives": 0})
    d = c.auto_tune("astronomy")
    assert d["action"] == "loosen"
    assert c.get("astronomy")["cross_check_rel_tol"] > before   # gained sensitivity room


def test_false_positive_forces_rollback(tmp_path):
    c = _cal(tmp_path)
    # first a safe run establishes last_safe + loosens
    c.record_benchmark("astronomy", {"positives_total": 3, "positives_correct": 1,
                                     "nulls_total": 3, "nulls_correct": 3,
                                     "false_positives": 0})
    c.auto_tune("astronomy")
    loosened = c.get("astronomy")["cross_check_rel_tol"]
    # now a null comes back positive → specificity violated → rollback (stricter)
    c.record_benchmark("astronomy", {"positives_total": 3, "positives_correct": 2,
                                     "nulls_total": 3, "nulls_correct": 2,
                                     "false_positives": 1})
    d = c.auto_tune("astronomy")
    assert d["action"] == "rollback"
    assert c.get("astronomy")["cross_check_rel_tol"] < loosened   # tightened back


def test_tolerance_never_exceeds_bounds(tmp_path):
    c = _cal(tmp_path)
    lo, hi = BOUNDS["cross_check_rel_tol"]
    for _ in range(50):
        c.record_benchmark("x", {"positives_total": 3, "positives_correct": 0,
                                 "nulls_total": 3, "nulls_correct": 3,
                                 "false_positives": 0})
        c.auto_tune("x")
    assert lo <= c.get("x")["cross_check_rel_tol"] <= hi


def test_domains_are_independent(tmp_path):
    c = _cal(tmp_path)
    c.record_benchmark("astronomy", {"positives_total": 3, "positives_correct": 1,
                                     "nulls_total": 3, "nulls_correct": 3, "false_positives": 0})
    c.auto_tune("astronomy")
    # genomics untouched → still default
    assert c.get("genomics")["cross_check_rel_tol"] == DEFAULTS["cross_check_rel_tol"]


def test_summarize_counts_false_positives():
    results = [
        {"expected": "positive", "outcome": "positive_robust", "correct": True},
        {"expected": "positive", "outcome": "inconclusive", "correct": False},
        {"expected": "null", "outcome": "positive_robust", "correct": False},  # false pos
        {"expected": "null", "outcome": "refuted", "correct": True},
    ]
    s = summarize(results)
    assert s["false_positives"] == 1 and s["positives_correct"] == 1
    assert s["nulls_total"] == 2
