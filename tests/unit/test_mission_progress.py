"""Mission progress: smooth 0-100% from step weights + sub-fraction (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.missions import STEP_WEIGHT, MissionEngine


def _mk(steps):
    return {"status": "RUNNING", "steps": [dict(s) for s in steps]}


def test_pct_weights_and_running_subfraction():
    st = [{"name": n, "status": "PENDING", "sub_frac": 0.0}
          for n in ("investigate", "experiments_propose", "experiments_run", "synthesize")]
    m = _mk(st)
    assert MissionEngine._pct(m) == 0
    m["steps"][0]["status"] = "DONE"                   # 15/100
    assert MissionEngine._pct(m) == 15
    m["steps"][1]["status"] = "DONE"                   # 30/100
    m["steps"][2]["status"] = "RUNNING"
    m["steps"][2]["sub_frac"] = 0.5                    # +55*0.5 = 27.5 → 57 or 58
    p = MissionEngine._pct(m)
    assert 57 <= p <= 58
    # everything but synth done → 45 + 55 = ... but running never hits 100
    m["steps"][2]["status"] = "DONE"
    m["steps"][2]["sub_frac"] = 1.0
    assert MissionEngine._pct(m) == 85


def test_pct_caps_at_99_until_done_then_100():
    st = [{"name": n, "status": "DONE", "sub_frac": 1.0}
          for n in ("investigate", "experiments_propose", "experiments_run")]
    st.append({"name": "synthesize", "status": "RUNNING", "sub_frac": 0.99})
    m = _mk(st)
    assert MissionEngine._pct(m) == 99                 # never 100 while RUNNING
    m["status"] = "DONE"
    assert MissionEngine._pct(m) == 100


def test_weights_sum_to_100():
    assert sum(STEP_WEIGHT.values()) == 100


def test_real_offline_mission_reaches_100(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Prog", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    m = eng.store.get(r["mission_id"])
    assert m["status"] == "DONE" and m["progress_pct"] == 100
