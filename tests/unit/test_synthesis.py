"""C2: verdicts → World Model beliefs + auto-dossier (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.synthesis import synthesize_hypothesis


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Sintesis", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    return p, h, fl


def _fake_completed_exp(fl, pid, hid, verdict):
    e = fl.propose_experiments(pid, hid, use_ai=False)["created"][0]
    fl.store.update_payload(e["id"], {
        "status": "COMPLETE",
        "result": {"metrics": {"m": 1.0}, "verdict": verdict,
                   "verdict_reason": "r",
                   "null_test": {"description": "d", "passed": True}}},
        status="COMPLETE")
    return e


def test_synthesis_creates_world_node_and_dossier(session_factory):
    p, h, fl = _setup(session_factory)
    _fake_completed_exp(fl, p.id, h["id"], "supports")
    out = synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    assert out["ok"] is True
    assert out["belief"]["node_id"].startswith("")
    assert out["belief"]["confidence"] is not None
    assert len(out["belief"]["applied_now"]) == 1
    # dossier draft exists, honest readiness
    d = next(d for d in fl.store.list_objects(p.id, kind="dossier")
             if d.get("hyp_id") == h["id"])
    assert d["status"] == "DRAFT" and "revisión humana" in d["readiness"]
    assert d["evidence_for"]                       # supports listed
    assert d["belief_confidence"] == out["belief"]["confidence"]


def test_belief_updates_are_idempotent(session_factory):
    p, h, fl = _setup(session_factory)
    _fake_completed_exp(fl, p.id, h["id"], "supports")
    o1 = synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    o2 = synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    assert len(o1["belief"]["applied_now"]) == 1
    assert len(o2["belief"]["applied_now"]) == 0     # same experiment NOT re-applied
    assert o2["belief"]["confidence"] == o1["belief"]["confidence"]


def test_refutes_lowers_confidence_vs_supports(session_factory):
    p1, h1, fl1 = _setup(session_factory)
    _fake_completed_exp(fl1, p1.id, h1["id"], "supports")
    up = synthesize_hypothesis(p1.id, h1["id"], session_factory, use_ai=False)

    lg = ResearchLedger(session_factory)
    p2 = lg.create_project("Sintesis2", domain="astronomy")
    h2 = HypothesisService(session_factory).generate(p2.id, use_ai=False)["created"][0]
    fl2 = HypothesisFlow(session_factory)
    fl2.set_status(p2.id, h2["id"], "APPROVED", "x")
    _fake_completed_exp(fl2, p2.id, h2["id"], "refutes")
    down = synthesize_hypothesis(p2.id, h2["id"], session_factory, use_ai=False)

    assert down["standing"].startswith("DEBILITADA")
    assert up["standing"].startswith("APOYADA")
    assert down["belief"]["confidence"] < up["belief"]["confidence"]


def test_dossier_is_upserted_not_duplicated(session_factory):
    p, h, fl = _setup(session_factory)
    synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    ds = [d for d in fl.store.list_objects(p.id, kind="dossier")
          if d.get("hyp_id") == h["id"]]
    assert len(ds) == 1


def test_dossier_carries_critic_block(session_factory):
    p, h, fl = _setup(session_factory)
    from acero.portal.critic import CriticAgent
    CriticAgent(session_factory).critique_now(
        p.id, h["id"], "hipotesis", "ctx", use_ai=False)
    synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    d = next(d for d in fl.store.list_objects(p.id, kind="dossier")
             if d.get("hyp_id") == h["id"])
    assert d["critic"] is not None and d["critic"]["verdict"] == "sin_revision"
