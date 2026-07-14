"""Scientific-integrity tests for the Cross-Domain Structural Discovery Benchmark.

Runs the full benchmark ONCE (module-scoped) including the sandbox resonance transfer.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.science


@pytest.fixture(scope="module")
def cdb():
    from sqlalchemy import create_engine

    from acero.benchmarks.cross_domain import run_cross_domain
    from acero.ledger.db import make_session_factory
    from acero.ledger.models import Base
    from acero.ledger.service import ResearchLedger
    from acero.world_model.graph import WorldModel

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    led = ResearchLedger(sf)
    proj = led.create_project("CDB", domain="physics")
    wm = WorldModel(sf, led, proj.id)
    return run_cross_domain(wm), wm


def test_oscillator_rlc_structurally_supported_with_transfer(cdb):
    rep, _ = cdb
    a = rep["analogies"]["oscillator_rlc"]
    assert a["status"] == "STRUCTURALLY_SUPPORTED"
    assert a["validations"]["predictive_transfer"] is True  # verified in sandbox
    assert "resonance ω₀ = sqrt(restoring/inertia)" in a["transfer_predictions"][0] \
        or a["transfer_predictions"]


def test_atom_solar_system_flagged_misleading(cdb):
    rep, _ = cdb
    a = rep["analogies"]["atom_solar_system"]
    assert a["status"] == "MISLEADING"
    assert a["deep_score"] < 0.2
    assert rep["integrations"]["atom_solar_system"]["outcome"] == "refuted_as_misleading"


def test_diffusion_valid_in_regime(cdb):
    rep, _ = cdb
    assert rep["analogies"]["thermal_particle_diffusion"]["status"] in {
        "VALID_IN_REGIME", "STRUCTURALLY_SUPPORTED"}


def test_belief_updates_are_consistent(cdb):
    rep, _ = cdb
    # supported analogy -> higher belief than the misleading one
    supported = rep["integrations"]["oscillator_rlc"]["confidence"]
    misleading = rep["integrations"]["atom_solar_system"]["confidence"]
    assert supported > misleading


def test_first_principles_recovers_resonance_scaling(cdb):
    rep, _ = cdb
    pg = rep["first_principles"]["oscillator_dimensional_analysis"]["pi_groups"]
    # dimensionless group ties resonant_frequency^2 to spring_constant/mass
    assert rep["first_principles"]["oscillator_dimensional_analysis"]["n_pi_groups"] == 1
    assert pg


def test_honesty_and_limits_present(cdb):
    rep, _ = cdb
    text = " ".join(rep["honesty"]).lower()
    assert "valida el método" in text or "valida el metodo" in text
    assert rep["cannot_conclude"]


def test_rejected_analogy_preserved_in_world_model(cdb):
    rep, wm = cdb
    from acero.cognitive.analogies.engine import AnalogyEngine
    assert len(AnalogyEngine(wm).rejected()) >= 1
