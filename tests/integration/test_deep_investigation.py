"""Deep investigation: Hubble tension (real data) + multi-angle orchestration."""

from __future__ import annotations

import pytest

from acero.studies import hubble_tension


def _hubble_available() -> bool:
    return hubble_tension._dataset().exists() and len(hubble_tension.load_rows()) > 20


def test_hubble_tension_from_real_data():
    if not _hubble_available():
        pytest.skip("Hubble dataset not present")
    r = hubble_tension.analyze()
    assert r["ok"] is True
    assert r["n_measurements"] >= 30
    # early-universe H0 ~67-69, late-universe ~72-74 (real, well-known values)
    assert 66 < r["early_universe"]["weighted_H0"] < 70
    assert 71 < r["late_universe"]["weighted_H0"] < 75
    # a real, significant tension
    assert r["tension_sigma"] >= 3.0 and r["significant_tension"] is True


def test_hubble_makes_no_discovery():
    if not _hubble_available():
        pytest.skip("dataset not present")
    r = hubble_tension.analyze()
    pro = " ".join(r["prohibited_claims"]).lower()
    assert "resolver la tensión" in pro
    assert r["cannot_conclude"]


def test_deep_investigation_records_real_artifacts(session_factory):
    if not _hubble_available():
        pytest.skip("dataset not present")
    import urllib.request
    try:
        urllib.request.urlopen("https://api.crossref.org/works?rows=1", timeout=10)
    except Exception:  # noqa: BLE001
        pytest.skip("offline (Crossref unreachable)")
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    from acero.studies.place_in_universe import investigate
    lg = ResearchLedger(session_factory)
    proj = lg.create_project("place test", domain="astronomy")
    r = investigate(proj.id, session_factory=session_factory, synthesize=False)
    assert r["ok"] is True
    assert r["n_angles"] == 5
    assert r["is_discovery"] is False
    store = DiscoveryStore(session_factory, lg)
    # real literature references and real-data experiments were recorded
    assert len(store.list_objects(proj.id, kind="literature")) >= 3
    exps = store.list_objects(proj.id, kind="experiment")
    assert exps and all(e.get("synthetic") is False for e in exps)
    assert store.list_objects(proj.id, kind="dossier")
