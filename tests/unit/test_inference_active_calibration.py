"""Discriminating experiments, calibration, and abstention tests."""
from __future__ import annotations

import numpy as np

from acero.inference.active_experiments.discriminating import design
from acero.inference.calibration import calibration
from acero.inference.data.observations import generate
from acero.inference.engine import StructureInferenceEngine
from acero.inference.models import StructureInferenceProblem


def test_discriminating_experiment_picks_divergent_ic():
    exp = design(lambda s: np.array([-0.7 * s[0]]),
                 lambda s: np.array([-0.7 * s[0] * (1 - s[0] / 200.0)]),
                 ["x"], candidate_ics=[{"x": 2.0}, {"x": 180.0}], t_max=6.0)
    assert exp.initial_conditions["x"] == 180.0   # high amplitude discriminates
    assert exp.predicted_divergence > 0
    assert exp.expected_information_gain > 0
    assert exp.failure_modes


def test_calibration_detects_overconfidence():
    # confidences all 0.9 but only 50% correct -> miscalibrated, high error
    conf = [0.9] * 20
    correct = [True] * 10 + [False] * 10
    res = calibration.calibrate(conf, correct)
    assert res.calibration_error > 0.3
    assert res.brier_score > 0.1


def test_calibration_wellcalibrated_low_error():
    rng = np.random.default_rng(0)
    conf, correct = [], []
    for _ in range(500):
        p = float(rng.uniform(0, 1))
        conf.append(p)
        correct.append(bool(rng.uniform() < p))
    res = calibration.calibrate(conf, correct, n_bins=10)
    assert res.calibration_error < 0.1


def test_interval_coverage():
    cov = calibration.interval_coverage([1, 2, 3], [0, 1, 2], [2, 3, 4], [1.5, 2.5, 5.0])
    assert cov["coverage"] == round(2 / 3, 4)


def test_empty_bins_handled():
    res = calibration.calibrate([0.95, 0.96], [True, True])
    assert any(b["count"] == 0 for b in res.reliability)  # low bins empty


def test_abstains_on_insufficient_data():
    obs = generate("damped", seed=1, n=20, t_max=2.0)  # too few
    E = StructureInferenceEngine(min_samples=40)
    rep = E.infer(StructureInferenceProblem(project_id="p", phenomenon="d",
                                            variables_observed=obs.variables), obs)
    assert rep["abstention"]["abstains"]
    assert any("insufficient" in r for r in rep["abstention"]["reasons"])


def test_engine_discloses_sindy_and_derivative_caveats():
    # Regression for the adversarial-audit fixes.
    obs = generate("damped", seed=1, n=400, t_max=8.0)
    E = StructureInferenceEngine()
    rep = E.infer(StructureInferenceProblem(project_id="p", phenomenon="d",
                                            variables_observed=obs.variables), obs)
    text = " ".join(rep["honesty"]).lower()
    assert "sindy" in text                       # same-data derivative caveat disclosed
    assert "calibrad" in text                     # coefficients lack calibrated uncertainty
    assert "coefficient_note" in rep
    assert any("derivative" in imp for imp in rep["imposed"])
