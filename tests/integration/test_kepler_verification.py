"""Real-data Kepler's Third Law verification (public NASA data)."""

from __future__ import annotations

import pytest

from acero.studies import kepler_law


def _data_available() -> bool:
    return kepler_law._dataset().exists() and len(kepler_law.load_rows()) > 500


def test_kepler_third_law_holds_on_real_data():
    if not _data_available():
        pytest.skip("NASA exoplanet dataset not present")
    r = kepler_law.verify()
    assert r["ok"] is True
    assert r["n_planets"] > 1000
    # Newton/Kepler theory: alpha=1.5, beta=-0.5, tight fit
    assert abs(r["fitted"]["alpha_log_a"] - 1.5) < 0.05
    assert abs(r["fitted"]["beta_log_M"] - (-0.5)) < 0.1
    assert r["fitted"]["r_squared"] > 0.95
    assert r["consistent_with_kepler"] is True
    # Earth's 1 AU / 1 Msun orbit fits the universal relation to a few percent
    assert r["earth_context"]["frac_error"] < 0.05


def test_verification_is_not_a_discovery():
    if not _data_available():
        pytest.skip("dataset not present")
    r = kepler_law.verify()
    pro = " ".join(r["prohibited_claims"]).lower()
    assert "descubrir" in pro
    assert "verifica una ley conocida" in r["claim"].lower()


def test_run_real_data_verification_records_experiment(session_factory):
    if not _data_available():
        pytest.skip("dataset not present")
    from acero.ledger.service import ResearchLedger
    from acero.portal.copilot import run_real_data_verification
    lg = ResearchLedger(session_factory)
    proj = lg.create_project("Earth position test", domain="astronomy")
    out = run_real_data_verification(proj.id, session_factory=session_factory)
    assert out["ok"] is True
    assert out["is_discovery"] is False
    assert out["experiment_id"] and out["world_node"]
    # the experiment is recorded as REAL (not synthetic)
    from acero.discovery.store import DiscoveryStore
    store = DiscoveryStore(session_factory, lg)
    exps = store.list_objects(proj.id, kind="experiment")
    assert exps and exps[0]["synthetic"] is False
