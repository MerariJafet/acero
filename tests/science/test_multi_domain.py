"""Sprint 10 science tests: multi-domain reasoning + gate-bypass benchmarks."""

from __future__ import annotations

from acero.benchmarks.gate_bypass import run_gate_bypass
from acero.benchmarks.multi_domain import run_multi_domain


def test_all_tracks_present():
    r = run_multi_domain()
    assert set(r) == {"track_physics", "track_astronomy", "track_genetics",
                      "track_chemistry", "cross_domain_transfer"}


def test_physics_track_flags_and_blocks_false_evidence():
    r = run_multi_domain()["track_physics"]
    assert r["cases_passed"] == r["n"]
    assert r["false_evidence_flagged"] and r["gate_blocks_false_evidence"]


def test_astronomy_track_abstains_and_blocks_causal():
    r = run_multi_domain()["track_astronomy"]
    assert r["abstains_on_mechanism"]
    assert r["gate_blocks_causal_from_association"]


def test_genetics_track_corrects_and_blocks_causality():
    r = run_multi_domain()["track_genetics"]
    assert r["population_confound_removed"]
    assert r["multiple_testing_corrected"]
    assert r["gate_blocks_false_causality"]


def test_chemistry_track_detects_nonident_and_blocks_stoichiometry():
    r = run_multi_domain()["track_chemistry"]
    assert r["nonidentifiability_detected"]
    assert r["gate_blocks_stoichiometry_violation"]


def test_cross_domain_transfer_shares_structure_not_mechanism():
    r = run_multi_domain()["cross_domain_transfer"]
    assert r["shared_saturation_structure"]
    assert not r["same_mechanism_claimed"]
    assert r["transfer_valid_but_not_identity"]


def test_gate_bypass_all_blocked():
    r = run_gate_bypass()
    assert r["all_blocked"]
    assert r["n_blocked"] == r["n"] == 7
