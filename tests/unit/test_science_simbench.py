"""CCC-7: simulation & recovery bench measures real operating characteristics."""

from __future__ import annotations

from acero.science.simbench import (
    evaluate,
    gen_confounded,
    gen_no_effect,
    naive_ttest,
    run_scenario,
)


def test_bench_measures_controlled_fpr_and_high_power():
    rep = evaluate(naive_ttest(), n_reps=120, n=200)
    # a correct test has ~nominal false positives and good power on a strong effect
    assert rep.fpr <= 0.12
    assert rep.power_strong >= 0.8
    assert abs(rep.bias_strong) < 0.15         # unbiased on the true effect


def test_bench_exposes_confounding_and_batch():
    rep = evaluate(naive_ttest(), n_reps=120, n=200)
    # the naive (unadjusted) method IS fooled by confounding & batch — the bench reveals it
    assert rep.false_effect_confounded > 0.5
    assert rep.false_effect_batch > 0.4
    # therefore: fine for ASSOCIATION claims, NOT fit for CAUSAL claims
    assert rep.passes_association() is True
    assert rep.passes_causal() is False


def test_bench_flags_leakage_as_trivially_detected():
    rep = evaluate(naive_ttest(), n_reps=60, n=200)
    assert rep.leakage_detected >= 0.99        # leakage ⇒ near-perfect apparent effect


def test_no_effect_scenario_truth_is_null():
    res = run_scenario(naive_ttest(), gen_no_effect, n_reps=50, n=150)
    assert res.has_effect is False and res.detection_rate <= 0.15


def test_confounded_truth_has_no_causal_effect():
    _, truth = gen_confounded(seed=7)
    assert truth.has_effect is False and "confusión" in truth.mechanism
