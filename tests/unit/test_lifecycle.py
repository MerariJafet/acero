"""Lifecycle: critique cascade, safe delete w/ vault memory, save/anchor, trace."""

from __future__ import annotations

import os
from pathlib import Path

from acero.ledger.service import ResearchLedger
from acero.portal.critic import CriticAgent
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.lifecycle import Lifecycle


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Vida", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    return p, h, fl


def _exp(fl, pid, hid, **extra):
    e = fl.propose_experiments(pid, hid, use_ai=False)["created"][0]
    if extra:
        fl.store.update_payload(e["id"], extra)
    return e


def test_consider_critique_reversions_whole_flow(session_factory):
    p, h, fl = _setup(session_factory)
    e = _exp(fl, p.id, h["id"], status="COMPLETE",
             result={"metrics": {"m": 1}, "verdict": "supports",
                     "verdict_reason": "r"})
    # critique targets the EXPERIMENT; cascade must reach the hypothesis
    c = CriticAgent(session_factory).critique_now(
        p.id, e["id"], "experimento_resultado", "ctx", use_ai=False)
    lc = Lifecycle(session_factory)
    out = lc.consider_critique(p.id, c["id"])
    assert out["ok"] is True and out["version"] == 2
    hh = fl.store.get(h["id"])
    assert hh["version"] == 2 and hh["lit_status"] == "STALE"
    assert hh["history"][-1]["critique_id"] == c["id"]
    assert fl.store.get(e["id"])["superseded_by_critique"] == c["id"]


def test_delete_cascade_archives_to_vault_and_spares_saved(session_factory, tmp_path):
    p, h, fl = _setup(session_factory)
    e1 = _exp(fl, p.id, h["id"])
    e2 = fl.propose_experiments(p.id, h["id"], use_ai=False)["created"][0]
    fl.store.put(p.id, "literature", "lit_x",
                 {"id": "lit_x", "hyp_id": h["id"], "title": "P", "doi": "10.1/p"},
                 status="INDEXED", actor="t", summary="s")
    lc = Lifecycle(session_factory)
    lc.save_experiment(e1["id"])                       # this one must survive
    out = lc.delete_hypothesis(p.id, h["id"])
    assert out["ok"] is True
    assert fl.store.get(h["id"]) is None               # hypothesis gone
    assert fl.store.get(e2["id"]) is None              # unsaved experiment gone
    surv = fl.store.get(e1["id"])
    assert surv is not None and surv["hyp_id"] == ""   # saved → orphaned
    assert surv["orphaned_from"]["tag"] == h["tag"]
    # vault remembers what was done
    vault = Path(os.environ["ACERO_OBSIDIAN_VAULT"])
    notes = list(vault.rglob("Archivo/*.md"))
    assert notes and "BORRADA" in notes[0].read_text(encoding="utf-8")


def test_anchor_orphan_to_new_hypothesis_absorbs_evidence(session_factory):
    p, h, fl = _setup(session_factory)
    e = _exp(fl, p.id, h["id"], status="COMPLETE", saved=True,
             result={"metrics": {"m": 1}, "verdict": "refutes",
                     "verdict_reason": "r",
                     "null_test": {"description": "d", "passed": True}})
    lc = Lifecycle(session_factory)
    lc.delete_hypothesis(p.id, h["id"])
    h2 = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl.set_status(p.id, h2["id"], "APPROVED", "y")
    assert lc.orphan_experiments(p.id)                 # orphan visible
    out = lc.anchor_experiment(p.id, e["id"], h2["id"])
    assert out["ok"] is True
    # the receiving hypothesis absorbed the verdict into its belief
    hh2 = fl.store.get(h2["id"])
    assert e["id"] in (hh2.get("synthesized_exp_ids") or [])
    assert lc.orphan_experiments(p.id) == []


def test_trace_tells_the_full_story_in_order(session_factory):
    p, h, fl = _setup(session_factory)
    fl.store.update_payload(h["id"], {"confrontation": {
        "query_used": "q", "stance": "mixed", "improved_hypothesis": "mejor"},
        "lit_count": 4})
    fl.adopt_improved(p.id, h["id"])                   # v2
    _exp(fl, p.id, h["id"], status="COMPLETE",
         result={"metrics": {"m": 1}, "verdict": "refutes",
                 "verdict_reason": "razones", "anomalies": ["pico raro"]})
    from acero.portal.anomalies import AnomalyEngine
    AnomalyEngine(session_factory).harvest(p.id, use_ai=False)  # child hypothesis
    tr = Lifecycle(session_factory).trace(p.id, h["id"])
    assert tr["ok"] is True and tr["version"] == 2
    types = [n["type"] for n in tr["nodes"]]
    assert "created" in types and "version" in types and "experiment" in types
    assert "child" in types                            # anomaly-born child linked
    child = next(n for n in tr["nodes"] if n["type"] == "child")
    assert "pico raro" in child["summary"]
    # nodes carry links to jump to the ficha
    assert any(n["link"] == "experimentos" for n in tr["nodes"])


def test_active_processes_lists_pending_missions(session_factory):
    p, h, fl = _setup(session_factory)
    from acero.portal.missions import MissionEngine
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=False)
    lc = Lifecycle(session_factory)
    procs = lc.active_processes()
    tags = [m["hyp_tag"] for m in procs["missions"]]
    assert h["tag"] in tags
    m = next(x for x in procs["missions"] if x["hyp_tag"] == h["tag"])
    assert m["project"].startswith("Vida") and m["hyp_version"] == 1
    # cleanup
    mm = eng.store.get(r["mission_id"])
    mm["status"] = "DONE"
    eng.store.update_payload(mm["id"], mm, status="DONE")
