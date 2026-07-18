"""Sprint 24 transit-program unit tests (fast, deterministic, no network)."""

from __future__ import annotations

import numpy as np

from acero.studies.transit import abstention, injection, nulls
from acero.studies.transit import pipelines as pl
from acero.studies.transit import preregistration as prereg


def test_preregistration_hash_stable():
    h1 = prereg.prereg_hash()
    h2 = prereg.prereg_hash()
    assert h1 == h2 and len(h1) == 64


def test_prohibited_claims_forbid_discovery():
    pro = " ".join(prereg.PREREGISTRATION["prohibited_claims"]).lower()
    assert "discovery of a new planet" in pro
    assert "independent replication" in pro


def test_inject_and_recover_synthetic():
    rng = np.random.default_rng(1)
    n = 3000
    time = np.cumsum(rng.uniform(0.019, 0.021, n))
    time -= time[0]
    base = 1.0 + rng.normal(0, 0.0015, n)
    inj = injection.inject_box(time, base, period=3.5, depth=0.01, duration_hours=3.2)
    res = pl.pipeline_a(time, inj, window=51, p_min=0.5, p_max=8.0)
    assert abs(res.period - 3.5) / 3.5 < 0.01          # recovered injected period
    assert res.snr >= 7.0


def test_null_flux_shuffled_finds_nothing():
    rng = np.random.default_rng(2)
    n = 3000
    time = np.cumsum(rng.uniform(0.019, 0.021, n))
    time -= time[0]
    base = 1.0 + rng.normal(0, 0.0015, n)
    inj = injection.inject_box(time, base, period=3.5, depth=0.01, duration_hours=3.2)
    out = nulls.null_flux_shuffled(time, inj)
    assert out["pass"] is True                          # destroyed signal -> no detection


def test_no_transit_synthetic_null_passes():
    out = nulls.null_no_transit_synthetic()
    assert out["pass"] is True


def test_calibration_monotone_suppresses_low_snr():
    cal = injection.recovery_vs_snr(snr_levels=[3.0, 20.0], trials=4)
    assert cal["low_snr_suppressed"] is True
    assert cal["high_snr_recovered"] is True


def test_abstention_fires_on_low_snr():
    thr = prereg.PREREGISTRATION["thresholds"]
    d = abstention.decide(
        snr=4.0, period_agreement={"agree_1pct": True, "frac_diff": 0.0},
        period_stability_frac=0.0,
        null_summary={"all_controlled": True, "false_positive_rate": 0.0},
        recovery_rate=0.95, quality_severe=False, n_indistinguishable_candidates=1,
        thresholds=thr)
    assert d.abstain is True
    assert any("SNR" in r for r in d.reasons)


def test_abstention_fires_on_pipeline_disagreement():
    thr = prereg.PREREGISTRATION["thresholds"]
    d = abstention.decide(
        snr=50.0, period_agreement={"agree_1pct": False, "frac_diff": 0.3},
        period_stability_frac=0.0,
        null_summary={"all_controlled": True, "false_positive_rate": 0.0},
        recovery_rate=0.95, quality_severe=False, n_indistinguishable_candidates=1,
        thresholds=thr)
    assert d.abstain is True
    assert any("disagree" in r for r in d.reasons)


def test_abstention_fires_on_wrong_period_recovery():
    # Codex #3: agreeing on a WRONG period is not recovery of the known transit.
    thr = prereg.PREREGISTRATION["thresholds"]
    d = abstention.decide(
        snr=50.0, period_agreement={"agree_1pct": True, "frac_diff": 0.0},
        period_stability_frac=0.001,
        null_summary={"all_controlled": True, "false_positive_rate": 0.0},
        recovery_rate=0.95, quality_severe=False, n_indistinguishable_candidates=1,
        thresholds=thr, period_recovery_frac=0.2)     # 20% from known ephemeris
    assert d.abstain is True
    assert any("known ephemeris" in r for r in d.reasons)


def test_abstention_fires_on_false_positive_scenarios():
    # Codex #6: computed false-positive scenarios must count against the claim.
    thr = prereg.PREREGISTRATION["thresholds"]
    d = abstention.decide(
        snr=50.0, period_agreement={"agree_1pct": True, "frac_diff": 0.0},
        period_stability_frac=0.001,
        null_summary={"all_controlled": True, "false_positive_rate": 0.0},
        recovery_rate=0.95, quality_severe=False, n_indistinguishable_candidates=1,
        thresholds=thr, period_recovery_frac=0.0, n_false_positive_scenarios=3)
    assert d.abstain is True
    assert any("false-positive scenario" in r for r in d.reasons)


def test_nulls_use_declared_detrend_window():
    # Codex #4: nulls/injection must use the preregistered Pipeline A window.
    assert pl.PIPELINE_A_WINDOW == prereg.PREREGISTRATION["detrending"]["A_median_window_points"]


def test_control_null_checks_both_pipelines():
    # Codex #5: the control-star null exposes false positives from EITHER pipeline.
    rng = np.random.default_rng(4)
    n = 3000
    time = np.cumsum(rng.uniform(0.019, 0.021, n))
    time -= time[0]
    flux = 1.0 + rng.normal(0, 0.0017, n)          # pure noise control
    out = nulls.null_control_star(time, flux, 3.52254)
    assert "pipeline_A" in out and "pipeline_B" in out
    assert out["pass"] is True                      # neither pipeline finds the target period


def test_transit_curriculum_has_blocking_concepts():
    from acero.understanding.curriculum.research_curriculum import CURRICULA, requirements_for
    assert "transit" in CURRICULA
    reqs = requirements_for("transit", "proj-x")
    concepts = {r.concept for r in reqs}
    assert {"recovery_is_not_discovery", "injection_is_not_observation",
            "same_data_not_independent", "when_to_abstain"} <= concepts
    blocking = {r.concept for r in reqs if r.blocking}
    assert "recovery_is_not_discovery" in blocking
    assert "same_data_not_independent" in blocking


def test_abstention_allows_only_when_all_clear():
    thr = prereg.PREREGISTRATION["thresholds"]
    d = abstention.decide(
        snr=50.0, period_agreement={"agree_1pct": True, "frac_diff": 0.0},
        period_stability_frac=0.001,
        null_summary={"all_controlled": True, "false_positive_rate": 0.0},
        recovery_rate=0.95, quality_severe=False, n_indistinguishable_candidates=1,
        thresholds=thr)
    assert d.abstain is False
    assert d.verdict == "RECOVERED_KNOWN_TRANSIT_UNDER_DECLARED_METHODS"
    assert "DISCOVER" not in d.verdict.upper()
