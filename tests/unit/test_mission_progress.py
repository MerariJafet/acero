"""Mission progress: smooth 0-100% from step weights + sub-fraction (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.missions import STEP_WEIGHT, MissionEngine


def _mk(steps):
    return {"status": "RUNNING", "steps": [dict(s) for s in steps]}


def test_pct_weights_and_running_subfraction():
    names = ("investigate", "experiments_propose", "experiments_run",
             "synthesize", "rigor_loop")
    st = [{"name": n, "status": "PENDING", "sub_frac": 0.0} for n in names]
    m = _mk(st)
    assert MissionEngine._pct(m) == 0
    m["steps"][0]["status"] = "DONE"                   # investigate 12
    assert MissionEngine._pct(m) == 12
    m["steps"][1]["status"] = "DONE"                   # +propose 12 → 24
    m["steps"][2]["status"] = "RUNNING"
    m["steps"][2]["sub_frac"] = 0.5                    # +run 46*0.5 = 23 → 47
    assert MissionEngine._pct(m) == 47
    m["steps"][2]["status"] = "DONE"                   # 12+12+46 = 70
    m["steps"][2]["sub_frac"] = 1.0
    assert MissionEngine._pct(m) == 70


def test_pct_caps_at_99_until_done_then_100():
    st = [{"name": n, "status": "DONE", "sub_frac": 1.0}
          for n in ("investigate", "experiments_propose", "experiments_run",
                    "synthesize")]
    st.append({"name": "rigor_loop", "status": "RUNNING", "sub_frac": 0.99})
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
