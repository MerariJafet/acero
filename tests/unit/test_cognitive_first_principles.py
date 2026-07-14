"""First Principles Engine tests."""

from __future__ import annotations

import numpy as np

from acero.cognitive.first_principles.engine import FirstPrinciplesEngine
from acero.cognitive.first_principles.models import (
    DerivationStep,
    FirstPrinciplesProblem,
    ScientificDerivation,
)


def test_dimensional_analysis_pendulum():
    fp = FirstPrinciplesEngine()
    prob = FirstPrinciplesProblem(project_id="p", phenomenon="pendulum",
                                  variables={"period": "time", "length": "length",
                                             "gravity": "acceleration", "mass": "mass"})
    res = fp.dimensional_analysis(prob)
    assert res["n_pi_groups"] == 1
    # audit fix: dimensional analysis discloses it gives scaling, not the constant
    assert "constant" in res["limitation"].lower()


def test_invalid_equation_rejected():
    fp = FirstPrinciplesEngine()
    assert not fp.validate_equation("force", "velocity")["consistent"]
    assert fp.validate_equation("force", "force")["consistent"]


def test_symmetry_to_conservation():
    fp = FirstPrinciplesEngine()
    res = {r["symmetry"]: r["conserved"] for r in
           fp.symmetry_conservation(["time_translation", "rotation", "scale"])}
    assert res["time_translation"] == "energy"
    assert res["rotation"] == "angular_momentum"
    assert res["scale"] is None


def test_conservation_check():
    fp = FirstPrinciplesEngine()
    ok = fp.check_conservation(["mass", "energy"], ["energy"])
    assert ok["ok"]
    bad = fp.check_conservation(["mass"], ["energy"])
    assert not bad["ok"] and "energy" in bad["missing"]


def test_derivation_verification_catches_bad_step():
    fp = FirstPrinciplesEngine()
    der = ScientificDerivation(project_id="p", target="test", steps=[
        DerivationStep(index=1, description="good", check_kind="symbolic",
                       expression="diff(exp(-k*t), t) - (-k*exp(-k*t))"),
        DerivationStep(index=2, description="bad", check_kind="symbolic",
                       expression="diff(t**2, t) - 3*t")])
    out = fp.verify(der)
    assert out.steps[0].verified
    assert not out.steps[1].verified
    assert out.unresolved_steps == [2]
    assert not out.all_verified
    assert out.confidence < 0.9  # Codex never certifies a derivation


def test_model_search_selects_minimal_and_flags_equivalence():
    fp = FirstPrinciplesEngine()
    x = np.linspace(0, 3, 50)
    y = 25 + 65 * np.exp(-0.7 * x) + np.random.default_rng(1).normal(0, 0.4, 50)
    xe = np.linspace(3, 5, 25)
    ye = 25 + 65 * np.exp(-0.7 * xe)
    res = fp.search_models(x, y, ["linear", "cubic", "exponential", "poly9"],
                           x_extra=xe, y_extra=ye)
    # poly9 may fit best in-sample, but the minimal adequate model is exponential.
    assert res["minimal_model"] == "exponential"
    assert len(res["observationally_equivalent"]) >= 2
    assert res["distinguishing_experiment"]["needed"]


def test_classification_prediction_is_not_explanation():
    fp = FirstPrinciplesEngine()
    res = fp.classify("poly9", mechanistic=False, causal=False, hidden_variables=False)
    assert "predicts but does not explain" in res["statements"]
