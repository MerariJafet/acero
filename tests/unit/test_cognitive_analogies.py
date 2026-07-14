"""Analogy Engine tests (no sandbox transfer in unit tests -> run_transfer=False)."""

from __future__ import annotations

import pytest

from acero.cognitive.analogies.engine import AnalogyEngine
from acero.cognitive.analogies.models import AnalogyStatus
from acero.cognitive.analogies.structure import compare, score
from acero.cognitive.analogies.systems import (
    ATOM,
    MECHANICAL_OSCILLATOR,
    PARTICLE_DIFFUSION,
    RLC_CIRCUIT,
    SOLAR_SYSTEM,
    THERMAL_DIFFUSION,
)
from acero.world_model.graph import WorldModel


@pytest.fixture()
def ae(session_factory, ledger, project) -> AnalogyEngine:
    return AnalogyEngine(WorldModel(session_factory, ledger, project.id))


def test_oscillator_rlc_recovers_mapping(ae):
    a = ae.build(MECHANICAL_OSCILLATOR, RLC_CIRCUIT, run_transfer=False)
    m = a.entity_mapping
    assert m["mass"] == "inductance"
    assert m["damping"] == "resistance"
    assert m["spring_constant"] == "inverse_capacitance"
    assert m["displacement"] == "charge"
    # structural + dimensional + mathematical pass without running the sandbox
    passed = {v.test for v in a.validations if v.passed}
    assert {"structural", "dimensional", "mathematical"} <= passed
    assert a.status in {AnalogyStatus.VALID_IN_REGIME, AnalogyStatus.STRUCTURALLY_SUPPORTED}
    assert a.scores.surface_similarity < 0.2  # different vocabulary


def test_surface_similarity_weighted_low():
    # A comparison with high surface but no deep structure must not score deep.
    comp = compare(ATOM, SOLAR_SYSTEM)
    s = score(comp)
    assert s.deep_score() < 0.3


def test_atom_solar_system_is_misleading(ae):
    a = ae.build(ATOM, SOLAR_SYSTEM, run_transfer=False)
    assert a.status == AnalogyStatus.MISLEADING
    assert a.failure_conditions
    counter = next(v for v in a.validations if v.test == "counterexample")
    assert not counter.passed


def test_diffusion_is_valid_in_regime(ae):
    a = ae.build(THERMAL_DIFFUSION, PARTICLE_DIFFUSION, run_transfer=False)
    assert a.status in {AnalogyStatus.VALID_IN_REGIME, AnalogyStatus.STRUCTURALLY_SUPPORTED}
    passed = {v.test for v in a.validations if v.passed}
    assert "dimensional" in passed  # fourier number verified dimensionless in both


def test_rejected_analogies_are_preserved(ae):
    ae.build(ATOM, SOLAR_SYSTEM, run_transfer=False)
    assert len(ae.rejected()) == 1  # misleading analogy kept as evidence


# --- regression tests for adversarial-audit fixes ---
def test_valid_analogy_states_regime_limits(ae):
    a = ae.build(MECHANICAL_OSCILLATOR, RLC_CIRCUIT, run_transfer=False)
    assert a.failure_conditions  # audit fix: even valid analogies state where they break
    assert any("nonlinear" in fc for fc in a.failure_conditions)


def test_diffusion_has_transfer_prediction(ae):
    a = ae.build(THERMAL_DIFFUSION, PARTICLE_DIFFUSION, run_transfer=False)
    assert a.transfer_predictions
    assert any("sqrt(D" in p for p in a.transfer_predictions)


def test_deep_score_is_low_precision(ae):
    a = ae.build(MECHANICAL_OSCILLATOR, RLC_CIRCUIT, run_transfer=False)
    s = a.scores.deep_score()
    assert round(s, 2) == s  # audit fix: no false precision (2 dp)


def test_dimensional_mismatch_would_break():
    # Swap RLC's restoring dimension to a wrong one -> dimensional test fails.
    from acero.cognitive.analogies.validation import dimensional_test
    bad = RLC_CIRCUIT.model_copy(deep=True)
    bad.variables["inverse_capacitance"] = "mass"  # wrong dimension
    res = dimensional_test(MECHANICAL_OSCILLATOR, bad)
    assert not res.passed
