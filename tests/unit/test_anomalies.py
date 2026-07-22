"""C5: measured discrepancies → new candidate hypotheses (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.anomalies import AnomalyEngine
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Anom", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    return p, h, fl


def _completed_exp(fl, pid, hid, *, anomalies=None, verdict="supports"):
    e = fl.propose_experiments(pid, hid, use_ai=False)["created"][0]
    fl.store.update_payload(e["id"], {
        "status": "COMPLETE",
        "result": {"metrics": {"m": 1.0}, "verdict": verdict,
                   "verdict_reason": "razón del veredicto",
                   "null_test": {"description": "d", "passed": True},
                   "anomalies": anomalies or []}}, status="COMPLETE")
    return e


def test_reported_anomalies_become_hypotheses_with_provenance(session_factory):
    p, h, fl = _setup(session_factory)
    _completed_exp(fl, p.id, h["id"],
                   anomalies=["ventanas 1930-1960 con pico corrido a 9.8 años"])
    eng = AnomalyEngine(session_factory)
    out = eng.harvest(p.id, use_ai=False)
    assert len(out["created"]) == 1
    c = out["created"][0]
    assert c["origin"] == "anomaly" and c["kind"] == "novel"
    assert "1930-1960" in c["anomaly_provenance"]["anomaly"]
    assert c["status"] == "PROPOSED"          # human still approves


def test_harvest_is_idempotent_per_experiment(session_factory):
    p, h, fl = _setup(session_factory)
    _completed_exp(fl, p.id, h["id"], anomalies=["outlier en 1998"])
    eng = AnomalyEngine(session_factory)
    o1 = eng.harvest(p.id, use_ai=False)
    o2 = eng.harvest(p.id, use_ai=False)
    assert len(o1["created"]) == 1 and len(o2["created"]) == 0


def test_refuted_verdict_counts_as_discrepancy(session_factory):
    p, h, fl = _setup(session_factory)
    _completed_exp(fl, p.id, h["id"], verdict="refutes")
    pend = AnomalyEngine(session_factory).pending_anomalies(p.id)
    assert len(pend) == 1 and pend[0]["kind"] == "verdict"
    assert "refutes" in pend[0]["anomaly"]


def test_supports_without_anomalies_yields_nothing(session_factory):
    p, h, fl = _setup(session_factory)
    _completed_exp(fl, p.id, h["id"], verdict="supports")
    out = AnomalyEngine(session_factory).harvest(p.id, use_ai=False)
    assert out["created"] == []


def test_tags_continue_numbering(session_factory):
    p, h, fl = _setup(session_factory)
    n_before = len(fl.store.list_objects(p.id, kind="candidate"))
    _completed_exp(fl, p.id, h["id"], anomalies=["a1"])
    out = AnomalyEngine(session_factory).harvest(p.id, use_ai=False)
    assert out["created"][0]["tag"] == f"H{n_before}"
