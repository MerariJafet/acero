"""C3: the critic's loop closes — suggestions→experiments, re-review, rigor, gate."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.critic import CriticAgent
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.synthesis import synthesize_hypothesis


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Loop", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    return p, h, fl


def _crit_with(ag, pid, hid, **extra):
    rec = ag.critique_now(pid, hid, "hipotesis", "ctx", use_ai=False)
    if extra:
        ag.store.update_payload(rec["id"], extra)
        rec.update(extra)
    return rec


def test_suggestions_become_experiments(session_factory):
    p, h, fl = _setup(session_factory)
    ag = CriticAgent(session_factory)
    _crit_with(ag, p.id, h["id"],
               suggestions=["comparar contra surrogatos AR(1)", "probar otra máscara"])
    out = ag.suggestions_to_experiments(p.id, h["id"])
    assert out["ok"] is True and len(out["created"]) == 2
    exps = fl.experiments_for(p.id, h["id"])
    assert all(e["title"].startswith("[Revisor]") for e in exps)
    assert all(e.get("from_critique") for e in exps)


def test_no_suggestions_is_honest_error(session_factory):
    p, h, _ = _setup(session_factory)
    ag = CriticAgent(session_factory)
    _crit_with(ag, p.id, h["id"])          # offline critique has no suggestions
    assert ag.suggestions_to_experiments(p.id, h["id"])["ok"] is False


def test_resolve_objections_offline_stays_pending(session_factory):
    p, h, _ = _setup(session_factory)
    ag = CriticAgent(session_factory)
    c = _crit_with(ag, p.id, h["id"], objections=["falta control nulo", "n muy chico"])
    out = ag.resolve_objections(p.id, h["id"], use_ai=False)
    assert out["resolved"] == 0 and out["pending"] == 2   # sin evidencia no se resuelve
    stored = ag.store.get(c["id"])
    assert stored["objections_status"] == ["pending", "pending"]


def test_rigor_score_counts_resolved(session_factory):
    p, h, _ = _setup(session_factory)
    ag = CriticAgent(session_factory)
    c = _crit_with(ag, p.id, h["id"], objections=["a", "b", "c", "d"])
    ag.store.update_payload(c["id"], {
        "objections_status": ["resolved", "resolved", "resolved", "pending"]})
    r = ag.rigor_score(p.id)
    assert r["score"] == 7.5 and r["resolved"] == 3 and r["total"] == 4


def test_rigor_score_without_objections_is_none(session_factory):
    p, _, _ = _setup(session_factory)
    assert CriticAgent(session_factory).rigor_score(p.id)["score"] is None


def test_rigor_ignores_experiment_critiques(session_factory):
    """Running more experiments (each critiqued) must NOT dilute the rigor score."""
    p, h, fl = _setup(session_factory)
    ag = CriticAgent(session_factory)
    ch = _crit_with(ag, p.id, h["id"], objections=["a", "b"])
    ag.store.update_payload(ch["id"], {"objections_status": ["resolved", "pending"]})
    # a per-experiment critique with its own (unresolved) objections
    e = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]
    ce = ag.critique_now(p.id, e["id"], "experimento_resultado", "x", use_ai=False)
    ag.store.update_payload(ce["id"], {"objections": ["z1", "z2", "z3", "z4"],
                                       "objections_status": ["pending"] * 4})
    r = ag.rigor_score(p.id)
    # only the hypothesis critique counts: 1 of 2 resolved → 5.0, not diluted by the 4
    assert r["total"] == 2 and r["resolved"] == 1 and r["score"] == 5.0


def test_dossier_soft_gate_blocks_on_critical_pending(session_factory):
    p, h, fl = _setup(session_factory)
    ag = CriticAgent(session_factory)
    _crit_with(ag, p.id, h["id"], verdict="defectuoso",
               objections=["sin nulos", "narrativa post hoc"])
    synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    d = next(d for d in fl.store.list_objects(p.id, kind="dossier")
             if d.get("hyp_id") == h["id"])
    assert d["blocked_by_critic"] is True
    assert "BLOQUEADO" in d["readiness"]
    assert d["critic"]["pending"] == 2


def test_dossier_unblocks_when_objections_resolved(session_factory):
    p, h, fl = _setup(session_factory)
    ag = CriticAgent(session_factory)
    c = _crit_with(ag, p.id, h["id"], verdict="defectuoso", objections=["sin nulos"])
    ag.store.update_payload(c["id"], {"objections_status": ["resolved"]})
    synthesize_hypothesis(p.id, h["id"], session_factory, use_ai=False)
    d = next(d for d in fl.store.list_objects(p.id, kind="dossier")
             if d.get("hyp_id") == h["id"])
    assert d["blocked_by_critic"] is False
    assert "BORRADOR_AUTOMATICO" in d["readiness"]
