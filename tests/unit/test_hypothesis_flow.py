"""Hypothesis-centric flow: approve → literature → experiments (offline)."""

from __future__ import annotations

import pytest

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow


@pytest.fixture()
def setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Flow", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    return session_factory, p.id, h


def test_approve_requires_reason(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    assert fl.set_status(pid, h["id"], "APPROVED")["ok"] is False
    assert fl.set_status(pid, h["id"], "APPROVED", "cuestiona la nula")["ok"] is True
    assert len(fl.approved(pid)) == 1


def test_reject_and_unapprove(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    fl.set_status(pid, h["id"], "PROPOSED")
    assert len(fl.approved(pid)) == 0


def test_propose_and_run_experiment_plan_only(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    exps = fl.propose_experiments(pid, h["id"], use_ai=False)["created"]
    assert exps
    run = fl.run_experiment(pid, exps[0]["id"], use_ai=False)
    # a generic proposed experiment has no code to run → reproducible PLAN, not a result
    assert run["mode"] == "plan_only"
    assert "plan" in run and "no es un resultado" in run["note"].lower()


def test_run_experiment_maps_to_real_analysis(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    e = fl.propose_experiments(pid, h["id"], use_ai=False)["created"][0]
    fl.store.update_payload(e["id"], {"data_source": "NASA exoplanet catalog, tercera ley de Kepler"})
    run = fl.run_experiment(pid, e["id"], use_ai=False)
    assert run["mode"] == "real_analysis"
    assert run["result"]["fitted"]["r_squared"] > 0.95


def test_hyp_tag_h0_does_not_trigger_hubble_runner(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    # a hypothesis literally tagged/titled "H0" must NOT match the Hubble runner
    assert fl._real_runner("H0: la señal es ruido") is None


def test_adopt_improved_versions_hypothesis(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    orig = fl.store.get(h["id"])["title"]
    # simulate a confrontation that produced an improved wording
    fl.store.update_payload(h["id"], {"confrontation": {
        "improved_hypothesis": "Versión afinada por la evidencia", "provider": "codex"}})
    res = fl.adopt_improved(pid, h["id"])
    assert res["ok"] is True and res["version"] == 2
    cur = fl.store.get(h["id"])
    assert cur["title"] == "Versión afinada por la evidencia"
    assert cur["version"] == 2
    assert cur["lit_status"] == "STALE"
    # v1 wording is archived in history
    assert cur["history"][0]["version"] == 1 and cur["history"][0]["title"] == orig


def test_adopt_improved_rejects_when_no_improvement(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    assert fl.adopt_improved(pid, h["id"])["ok"] is False  # no confrontation yet
    fl.store.update_payload(h["id"], {"confrontation": {
        "improved_hypothesis": fl.store.get(h["id"])["title"]}})
    # identical wording → nothing to adopt
    assert fl.adopt_improved(pid, h["id"])["ok"] is False


def test_experiments_seed_from_confrontation_ideas(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    fl.store.update_payload(h["id"], {"confrontation": {"experiment_ideas": [
        {"title": "Bajar curvas de luz de MAST", "approach": "descargar y ajustar",
         "data_source": "MAST TESS", "method_type": "download_data",
         "feasible_local": True}]}})
    created = fl.propose_experiments(pid, h["id"], use_ai=False)["created"]
    assert created
    assert created[0]["title"] == "Bajar curvas de luz de MAST"
    assert created[0]["method_type"] == "download_data"
