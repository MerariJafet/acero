"""Versioned label system: H vN → Inv vN → Aris vN.M (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.critic import CriticAgent
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Ver", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    return p, h, fl


def test_investigation_and_experiments_stamp_hyp_version(session_factory):
    p, h, fl = _setup(session_factory)
    fl.investigate(p.id, h["id"], use_ai=False)
    hh = fl.store.get(h["id"])
    assert hh["confrontation"]["hyp_version"] == 1
    e = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]
    assert e["hyp_version"] == 1


def test_aristoteles_labels_sequence_and_reset_on_new_version(session_factory):
    p, h, fl = _setup(session_factory)
    ag = CriticAgent(session_factory)
    c1 = ag.critique_now(p.id, h["id"], "hipotesis", "a", use_ai=False)
    c2 = ag.critique_now(p.id, h["id"], "literatura", "b", use_ai=False)
    assert c1["label"] == "Aris v1.1" and c2["label"] == "Aris v1.2"
    # bump the hypothesis to v2 → sequence restarts under the new version
    fl.store.update_payload(h["id"], {"version": 2,
                                      "confrontation": {"improved_hypothesis": "m2"}})
    c3 = ag.critique_now(p.id, h["id"], "hipotesis", "c", use_ai=False)
    assert c3["label"] == "Aris v2.1" and c3["hyp_version"] == 2


def test_experiment_critique_inherits_owner_version(session_factory):
    p, h, fl = _setup(session_factory)
    fl.store.update_payload(h["id"], {"version": 3})
    e = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]
    c = CriticAgent(session_factory).critique_now(
        p.id, e["id"], "experimento_resultado", "x", use_ai=False)
    assert c["hyp_version"] == 3 and c["label"] == "Aris v3.1"
