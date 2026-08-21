"""Mission Engine: autonomous per-hypothesis cycle with restart-safe checkpoints."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.missions import STEPS, MissionEngine


def _setup(session_factory, approve: bool = True):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Misión", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    if approve:
        fl.set_status(p.id, h["id"], "APPROVED", "vale")
    return p, h, fl


def test_mission_requires_approved_hypothesis(session_factory):
    p, h, _ = _setup(session_factory, approve=False)
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    assert r["ok"] is False and "APROBADAS" in r["error"]


def test_mission_full_cycle_offline(session_factory):
    p, h, fl = _setup(session_factory)
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    assert r["ok"] is True
    m = eng.store.get(r["mission_id"])
    assert m["status"] == "DONE"
    assert [s["status"] for s in m["steps"]] == ["DONE"] * len(STEPS)
    # the cycle really ran: literature done, experiments exist and were run
    hh = fl.store.get(h["id"])
    assert hh["lit_status"] == "DONE"
    exps = fl.experiments_for(p.id, h["id"])
    assert exps and all(e["status"] in ("PLANNED", "COMPLETE") for e in exps)
    # synthesis recorded the honest standing
    syn = eng.store.list_objects(p.id, kind="synthesis")
    assert syn and syn[0]["hyp_id"] == h["id"]
    assert "standing" in syn[0]


def test_mission_checkpoints_survive_restart(session_factory, monkeypatch):
    p, h, fl = _setup(session_factory)
    eng = MissionEngine(session_factory)

    # first run dies INSIDE experiments_propose (simulated crash mid-mission)
    boom = RuntimeError("proceso murió")
    orig = HypothesisFlow.propose_experiments
    monkeypatch.setattr(HypothesisFlow, "propose_experiments",
                        lambda self, pid, hid, use_ai=True: (_ for _ in ()).throw(boom))
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    m = eng.store.get(r["mission_id"])
    assert m["status"] == "FAILED"
    assert m["steps"][0]["status"] == "DONE"          # investigate checkpointed
    assert m["steps"][1]["status"] == "FAILED"

    # "restart": new engine, method restored, resume via retry
    monkeypatch.setattr(HypothesisFlow, "propose_experiments", orig)
    eng2 = MissionEngine(session_factory)
    rr = eng2.retry(r["mission_id"], sync=True)
    assert rr["ok"] is True
    m2 = eng2.store.get(r["mission_id"])
    assert m2["status"] == "DONE"
    # investigate was NOT re-run (checkpoint kept): still exactly one lit batch
    assert m2["steps"][0]["status"] == "DONE"


def test_resume_pending_picks_up_stale_running(session_factory):
    p, h, _ = _setup(session_factory)
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=False)  # queued async
    # simulate a dead worker: force RUNNING with an ancient heartbeat
    import time as _t
    m = eng.store.get(r["mission_id"])
    m["status"] = "RUNNING"
    m["heartbeat_ts"] = _t.time() - 9999
    eng.store.update_payload(m["id"], m, status="RUNNING")
    out = eng.resume_pending(sync=True)
    assert r["mission_id"] in out["resumed"]
    assert eng.store.get(r["mission_id"])["status"] == "DONE"


def test_no_duplicate_live_mission_per_hypothesis(session_factory):
    p, h, _ = _setup(session_factory)
    eng = MissionEngine(session_factory)
    m1 = eng.store  # keep store ref
    r1 = eng.start(p.id, h["id"], use_ai=False, sync=False)
    assert r1["ok"] is True
    r2 = eng.start(p.id, h["id"], use_ai=False, sync=False)
    assert r2["ok"] is False and "activa" in r2["error"]
    # cleanup: finish it synchronously so threads don't leak into other tests
    mm = m1.get(r1["mission_id"])
    mm["status"] = "DONE"
    m1.update_payload(mm["id"], mm, status="DONE")


def test_start_all_only_approved(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Todas", domain="astronomy")
    hs = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, hs[0]["id"], "APPROVED", "a")
    fl.set_status(p.id, hs[1]["id"], "APPROVED", "b")
    eng = MissionEngine(session_factory)
    out = eng.start_all(p.id, use_ai=False, sync=True)
    assert len(out["started"]) == 2
    assert all(m["status"] == "DONE" for m in eng.list_missions(p.id))


def test_resume_pending_revives_running_with_fresh_heartbeat(session_factory):
    """Reinicio del portal: un proceso recién nacido NO tiene workers, así que una
    misión RUNNING con heartbeat FRESCO también debe retomarse. (Bug 2026-08-21:
    confiar en el heartbeat aquí dejó 4 misiones zombis 8 horas — el reinicio las
    mató a <3 min de su último latido y quedaron 'vivas' para siempre.)"""
    import time as _t
    p, h, _ = _setup(session_factory)
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)   # sin pool global
    m = eng.store.get(r["mission_id"])
    m["status"] = "RUNNING"
    m["heartbeat_ts"] = _t.time() - 5          # latido de hace 5s: "fresco"
    eng.store.update_payload(m["id"], m, status="RUNNING")
    out = eng.resume_pending(sync=True)
    assert r["mission_id"] in out["resumed"]
    assert eng.store.get(r["mission_id"])["status"] == "DONE"


def test_watchdog_survives_malformed_mission_record(session_factory, monkeypatch):
    """Un objeto guardado con kind='mission' pero sin 'id'/'steps' (una nota vieja)
    NO puede matar el barrido: el watchdog lo salta y aun así recupera la misión
    zombi que viene después. (Bug 2026-08-21: un KeyError en ese registro tumbaba
    TODO el watchdog en silencio, cada 30s, durante horas.)"""
    import time as _t
    from acero.core.ids import new_id
    p, h, _ = _setup(session_factory)
    eng = MissionEngine(session_factory)
    # la nota malformada primero (kind=mission, payload sin 'id' ni 'steps')
    eng.store.put(p.id, "mission", new_id("msn"),
                  {"titulo": "nota vieja del meta-loop", "cerrada": "1"},
                  status="DONE", actor="test", summary="nota, no misión")
    # y una misión zombi real: RUNNING, sin worker, heartbeat viejo.
    # sync=True para NO tocar el pool global (_ACTIVE): con la suite completa la
    # misión encolada seguía en _ACTIVE al correr el watchdog y la decisión era
    # 'reap' en vez de 'resume' (carrera visible solo con el pool saturado).
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    m = eng.store.get(r["mission_id"])
    m["status"] = "RUNNING"
    m["heartbeat_ts"] = _t.time() - 9999
    eng.store.update_payload(m["id"], m, status="RUNNING")

    submitted: list[str] = []
    monkeypatch.setattr(eng, "_submit", lambda mid: submitted.append(mid))
    out = eng.watchdog()
    assert r["mission_id"] in out["resumed"]
    assert r["mission_id"] in submitted
    assert out["skipped_bad"]                 # la nota quedó registrada como saltada
