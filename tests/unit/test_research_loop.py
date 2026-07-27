"""Principal Investigator loop — decision, methodology bounds, tick side-effects,
pause/resume, and the event+interval driver. All offline: provider and the
mission/hypothesis services are injected, so no LLM or real mission runs."""
from __future__ import annotations

import pytest

from acero.ledger.service import ResearchLedger
from acero.portal import research_loop as rl
from acero.portal.hypotheses import HypothesisService
from acero.portal.research_loop import (
    PrincipalInvestigator,
    ResearchLoop,
    build_digest,
    is_paused,
    pause,
    resume,
)


@pytest.fixture(autouse=True)
def _loop_root(tmp_path, monkeypatch):
    monkeypatch.setenv("ACERO_LOOP_ROOT", str(tmp_path / "loop"))


# --- injected fakes -----------------------------------------------------------

class _Prov:
    def __init__(self, decision):
        self.decision = decision

    def available(self):
        return True

    def complete_json(self, prompt, schema, *, temperature=0.0):
        return self.decision


class _Engine:
    def __init__(self, missions=None):
        self.started = []
        self.missions = missions or []

    def start_all(self, pid, *, use_ai=True, sync=False):
        self.started.append(pid)
        return {"started": [{"hyp": "h1"}], "skipped": []}

    def list_missions(self, pid):
        return self.missions


class _Hyps:
    def __init__(self):
        self.calls = []

    def generate(self, pid, *, n=6, use_ai=True, focus=""):
        self.calls.append((n, focus))
        return {"ok": True, "created": [{"id": f"h{i}"} for i in range(n)]}


class _Flow:
    def __init__(self):
        self.approved = []

    def set_status(self, pid, hid, status, reason=""):
        self.approved.append((hid, status))


def _pi(provider, **kw):
    return PrincipalInvestigator(sf=None, provider=provider, engine=kw.get("engine"),
                                 hyps=kw.get("hyps"), flow=kw.get("flow"))


# --- decision + methodology bounds -------------------------------------------

def test_deterministic_bootstraps_then_chases_anomalies():
    pi = _pi(None)
    d0 = pi._deterministic({"hypotheses_by_status": {}})
    assert d0["action"] == "generate_and_run"
    d1 = pi._deterministic({"hypotheses_by_status": {"APPROVED": 2},
                            "open_anomalies": ["algo raro"]})
    assert d1["action"] == "generate_and_run" and d1["focus"]
    d2 = pi._deterministic({"hypotheses_by_status": {"APPROVED": 2}})
    assert d2["action"] == "run_existing"


def test_validate_clamps_and_coerces():
    pi = _pi(None)
    v = pi._validate({"action": "bogus", "n_new": 999})
    assert v["action"] == "run_existing" and v["n_new"] == 0
    v2 = pi._validate({"action": "generate_and_run", "n_new": 0})
    assert v2["n_new"] == 2                       # generate implies ≥ some new
    v3 = pi._validate({"action": "generate_and_run", "n_new": 50})
    assert v3["n_new"] == rl.MAX_NEW_HYP_PER_TICK


def test_decide_falls_back_when_provider_unavailable():
    class _Down:
        def available(self):
            return False
    d = _pi(_Down()).decide({"hypotheses_by_status": {}})
    assert d["action"] == "generate_and_run"      # deterministic path


# --- tick side effects (build_digest monkeypatched) ---------------------------

def _canned_digest(*a, **k):
    return {"hypotheses_by_status": {"APPROVED": 1}, "recent_verdicts": [],
            "open_anomalies": [], "rigor": {}}


def test_tick_generates_approves_and_starts(monkeypatch):
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    eng, hyp, flow = _Engine(), _Hyps(), _Flow()
    pi = _pi(_Prov({"action": "generate_and_run", "focus": "anomalías", "n_new": 3,
                    "reasoning": "x"}), engine=eng, hyps=hyp, flow=flow)
    rec = pi.tick("p1")
    assert len(hyp.calls) == 1 and hyp.calls[0][0] == 3
    assert hyp.calls[0][1].startswith("anomalías")        # + anti-HARKing steer
    assert len(flow.approved) == 3 and eng.started == ["p1"]
    assert rec["applied"]["started"] == 1 and rec["dry"] is False
    assert rl.load_state("p1")["ticks"] == 1


class _NoStart(_Engine):
    def start_all(self, pid, *, use_ai=True, sync=False):
        return {"started": [], "skipped": []}


class _NoHyps(_Hyps):
    def generate(self, pid, *, n=6, use_ai=True, focus=""):
        self.calls.append((n, focus))
        return {"ok": True, "created": []}


def test_tick_expands_frontier_when_nothing_to_run(monkeypatch):
    # PI picks 'deepen' but nothing is runnable (finished/empty project) →
    # self-correct by EXPANDING the frontier with new hypotheses, never dry-spin.
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    hyp, flow = _Hyps(), _Flow()
    pi = _pi(_Prov({"action": "deepen", "reasoning": "profundizar"}),
             engine=_NoStart(), hyps=hyp, flow=flow)
    rec = pi.tick("pb")
    assert rec["applied"].get("expanded") is True
    assert rec["applied"]["generated"] >= 2 and rec["applied"]["approved"] >= 2
    # nothing actually ran in this fake engine → dry (driver will back off), but
    # the frontier WAS expanded so a real engine would launch the new hypotheses
    assert rec["dry"] is True


def test_pi_pause_is_cooldown_not_stop(monkeypatch):
    # a PI 'pause' decision must NOT stop the loop (only the researcher pauses);
    # it is a cooldown: no work added, no missions started, treated as dry.
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    pi = _pi(_Prov({"action": "pause", "reasoning": "fricción operativa"}),
             engine=_Engine(), hyps=_Hyps(), flow=_Flow())
    rec = pi.tick("p2")
    assert rec["applied"].get("cooldown") is True
    assert rec["applied"]["started"] == 0 and rec["dry"] is True
    assert is_paused("p2") is False               # PI did NOT pause the loop


def test_dry_tick_increments_backoff_streak(monkeypatch):
    # truly dry: nothing runs AND the generator produces nothing new
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    pi = _pi(_Prov({"action": "run_existing", "reasoning": "x"}),
             engine=_NoStart(), hyps=_NoHyps(), flow=_Flow())
    pi.tick("p3")
    pi.tick("p3")
    assert rl.load_state("p3")["dry_streak"] == 2


# --- pause / resume -----------------------------------------------------------

def test_pause_resume_roundtrip():
    assert is_paused("p4") is False
    pause("p4")
    assert is_paused("p4") is True
    resume("p4")
    assert is_paused("p4") is False


# --- digest on a real in-memory project (no LLM) ------------------------------

def test_build_digest_summarizes_state(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Loop", domain="astronomy")
    HypothesisService(session_factory).generate(p.id, use_ai=False)
    dig = build_digest(session_factory, p.id)
    assert dig["project"]["title"] == "Loop"
    assert dig["n_hypotheses"] >= 1
    assert isinstance(dig["hypotheses_by_status"], dict)


# --- driver -------------------------------------------------------------------

class _FakePI:
    """Counts ticks; can pause itself on the Nth tick."""

    def __init__(self, engine, pause_on=None):
        self._engine = engine
        self.pause_on = pause_on
        self.ticks = 0

    def _engine_(self):
        return self._engine

    def tick(self, pid):
        self.ticks += 1
        if self.pause_on and self.ticks >= self.pause_on:
            pause(pid)
        return {"applied": {"started": 1}, "dry": False}


def test_run_stops_at_max_ticks():
    loop = ResearchLoop(sf=None, pi=_FakePI(_Engine()))
    out = loop.run("q1", max_ticks=3, wait=False)
    assert out["ticks"] == 3


def test_run_stops_when_paused_midloop():
    loop = ResearchLoop(sf=None, pi=_FakePI(_Engine(), pause_on=2))
    out = loop.run("q2", wait=False)              # unbounded, but pauses itself
    assert out["ticks"] == 2 and is_paused("q2")


def test_wait_returns_immediately_when_no_active_missions():
    loop = ResearchLoop(sf=None, pi=_FakePI(_Engine(missions=[])))
    slept = []
    loop._wait_for_missions("q3", interval_sec=100, poll_sec=5,
                            sleeper=lambda s: slept.append(s), clock=lambda: 0.0)
    assert slept == []                            # active==0 → no polling


def test_wait_polls_until_missions_finish():
    eng = _Engine(missions=[{"status": "RUNNING"}])
    loop = ResearchLoop(sf=None, pi=_FakePI(eng))
    t = {"v": 0.0}
    calls = {"n": 0}

    def _clock():
        return t["v"]

    def _sleep(s):
        t["v"] += s
        calls["n"] += 1
        if calls["n"] >= 2:
            eng.missions = []                     # missions finish after 2 polls
    loop._wait_for_missions("q4", interval_sec=100, poll_sec=5,
                            sleeper=_sleep, clock=_clock)
    assert calls["n"] == 2
