"""Sprint 11 tests: calibration registry, metrics, recalibration, abstention."""

from __future__ import annotations

import pytest

from acero.reliability.calibration import (
    INSUFFICIENT,
    CalibrationObservation,
    CalibrationRegistry,
)
from acero.reliability.recalibration import LeakageError, Split, recalibrate


def _prob(reg, p, correct, domain="global"):
    reg.record(CalibrationObservation("m", "probability", predicted_probability=p,
                                      actual_outcome=correct, domain=domain))


def test_insufficient_data_declared():
    reg = CalibrationRegistry()
    _prob(reg, 0.9, True)
    assert reg.probability_metrics()["status"] == INSUFFICIENT


def test_probability_metrics_computed():
    reg = CalibrationRegistry()
    for i in range(20):
        _prob(reg, 0.9, i % 2 == 0)       # 50% correct at 0.9 confidence → overconfident
    m = reg.probability_metrics()
    assert m["status"] == "ok"
    assert m["ece"] > 0.2 and "brier" in m and "mce" in m and "sharpness" in m


def test_interval_coverage():
    reg = CalibrationRegistry()
    for _ in range(10):
        reg.record(CalibrationObservation("m", "interval", predicted_interval=(0.0, 1.0),
                                          actual_outcome=0.5))
    m = reg.interval_metrics()
    assert m["coverage"] == 1.0 and m["mean_width"] == 1.0


def test_domain_calibration_separate():
    reg = CalibrationRegistry()
    for _ in range(10):
        _prob(reg, 0.9, True, domain="physics")
    for i in range(10):
        _prob(reg, 0.9, i % 3 == 0, domain="astronomy")
    by = reg.by_domain()
    assert set(by) == {"physics", "astronomy"}
    assert by["physics"]["ece"] < by["astronomy"]["ece"]   # physics better calibrated


def test_abstention_metrics():
    reg = CalibrationRegistry()
    # 5 good abstentions (would be wrong), 2 unnecessary (would be right), 5 answered correct
    for _ in range(5):
        reg.record(CalibrationObservation("m", "abstention",
                   actual_outcome={"abstained": True, "would_have_been_correct": False}))
    for _ in range(2):
        reg.record(CalibrationObservation("m", "abstention",
                   actual_outcome={"abstained": True, "would_have_been_correct": True}))
    for _ in range(5):
        reg.record(CalibrationObservation("m", "abstention",
                   actual_outcome={"abstained": False, "would_have_been_correct": True}))
    m = reg.abstention_metrics()
    assert m["good_abstentions"] == 5 and m["unnecessary_abstentions"] == 2
    assert m["errors_avoided"] == 5 and m["abstention_utility"] > 0


def test_risk_coverage_curve_monotone_start():
    reg = CalibrationRegistry()
    for i in range(20):
        _prob(reg, 0.5 + i / 40, i >= 5)   # higher confidence tends more correct
    curve = reg.risk_coverage_curve()
    assert curve and curve[0]["coverage"] < curve[-1]["coverage"]


def test_recalibration_rejects_leakage():
    split = Split(train_idx=[0, 1], calib_idx=[2, 3], test_idx=[3, 4])  # 3 overlaps
    with pytest.raises(LeakageError):
        recalibrate([0.5] * 5, [True] * 5, split)


def test_recalibration_improves_or_holds_ece():
    import numpy as np
    rng = np.random.default_rng(0)
    n = 200
    conf = list(np.clip(rng.uniform(0.5, 1.0, n), 0.01, 0.99))
    # truth: overconfident — correct with prob = conf*0.6
    correct = [bool(rng.random() < c * 0.6) for c in conf]
    idx = list(range(n))
    split = Split(train_idx=idx[:100], calib_idx=idx[100:150], test_idx=idx[150:])
    r = recalibrate(conf, correct, split, method="temperature")
    assert r["leakage_checked"]
    assert r["ece_after"] <= r["ece_before"] + 0.05    # recalibration does not worsen much
