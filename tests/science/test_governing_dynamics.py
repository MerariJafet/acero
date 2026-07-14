"""Scientific-integrity tests for the Governing Dynamics Inference Benchmark."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.science


@pytest.fixture(scope="module")
def bench():
    from acero.benchmarks.governing_dynamics import run_governing_dynamics
    return run_governing_dynamics()


def test_recovers_basic_systems(bench):
    rec = {k: v["recovered"] for k, v in bench["level1_recovery"].items()}
    assert rec["exponential_decay"] and rec["logistic"] and rec["damped"] and rec["predator_prey"]


def test_noise_degrades_monotonically(bench):
    r = bench["level2_noise"]
    assert r["0.0"]["r2_dv"] >= r["0.02"]["r2_dv"] >= r["0.1"]["r2_dv"]


def test_omitted_variable_flagged(bench):
    assert bench["level3_omitted_variable"]["missing_variable_flagged"]
    assert not bench["level3_omitted_variable"]["invented_variable_as_certain"]


def test_no_definitive_winner_for_equivalent_models(bench):
    assert bench["level4_equivalence"]["declared_winner"] is None
    assert bench["level4_equivalence"]["chose_high_amplitude_ic"]


def test_regime_change_detected(bench):
    assert bench["level5_regime"]["regime_change_detected"]


def test_conservation_recovered(bench):
    assert bench["level6_conservation"]["classification"] in {"exact", "approximate"}
    assert bench["level6_conservation"]["survives_noise"]


def test_gate_blocks_adversarial(bench):
    assert bench["level7_adversarial_gate"]["blocked"]
    assert bench["level7_adversarial_gate"]["n_blockers"] >= 6


def test_honesty_declares_imposed_library(bench):
    text = " ".join(bench["honesty"]).lower()
    assert "impuesta" in text
    assert "no" in text and "ley" in text
