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


def test_watchdog_submit_false_diagnostica_sin_ejecutar(session_factory, monkeypatch):
    """EL AUDITOR OBSERVA, NO EJECUTA. _submit() encola en un pool de hilos
    NO-daemon: un proceso efímero (cron) no puede salir hasta que la misión
    termine, así que un diagnóstico de 0,4 s se colgaba horas corriendo ciencia
    que no le tocaba (2026-08-21). Con submit=False detecta y reporta igual."""
    import time as _t
    p, h, _ = _setup(session_factory)
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    m = eng.store.get(r["mission_id"])
    m["status"] = "RUNNING"
    m["heartbeat_ts"] = _t.time() - 9999          # worker desaparecido
    eng.store.update_payload(m["id"], m, status="RUNNING")

    submitted: list[str] = []
    monkeypatch.setattr(eng, "_submit", lambda mid: submitted.append(mid))
    out = eng.watchdog(submit=False)
    assert r["mission_id"] in out["resumed"]       # la DETECTA
    assert submitted == []                         # pero NO la ejecuta


def test_watchdog_periodico_arranca_como_daemon_y_barre_solo(monkeypatch):
    """El auto-sanador no puede depender de que un humano abra el dashboard:
    _maybe_watchdog() solo se dispara desde list_missions(). Con el panel
    cerrado unas horas aparecieron 4 zombis que nadie recuperaba (2026-08-21)."""
    import threading as _th
    from acero.portal import missions as ms
    barridos = {"n": 0}

    class _Eng:
        def watchdog(self, **kw):
            barridos["n"] += 1
            raise SystemExit                      # corta el bucle tras 1 barrido

    # conftest apaga las misiones en toda la suite; aquí probamos justo el arranque
    monkeypatch.delenv("ACERO_MISSIONS_DISABLED", raising=False)
    monkeypatch.setattr(ms, "MissionEngine", lambda *a, **k: _Eng())
    hilo = ms.watchdog_loop_on_startup(interval_sec=0.01)
    assert hilo is not None
    assert hilo.daemon        # NUNCA debe impedir que el proceso termine
    assert hilo.name == "mission-watchdog"


def test_watchdog_periodico_respeta_el_interruptor_de_misiones(monkeypatch):
    import threading as _th
    from acero.portal import missions as ms
    monkeypatch.setenv("ACERO_MISSIONS_DISABLED", "1")
    assert ms.watchdog_loop_on_startup(interval_sec=0.01) is None


def test_submit_marca_el_latido_al_encolar(session_factory, monkeypatch):
    """El pool corre MAX_MISSIONS a la vez; la que espera turno no ejecuta
    _execute() y nadie late por ella. Desde fuera (el Auditor es otro proceso y
    no ve _ACTIVE) parecía MUERTA estando solo en cola — 2026-08-21: 8 misiones
    'RUNNING' con 4 workers. Encolar debe decir la verdad: la tengo en la mano."""
    import time as _t
    p, h, _ = _setup(session_factory)
    eng = MissionEngine(session_factory)
    r = eng.start(p.id, h["id"], use_ai=False, sync=True)
    mid = r["mission_id"]
    # simula una misión vieja sin latir, ya encolada por otro camino
    m = eng.store.get(mid)
    m["heartbeat_ts"] = _t.time() - 9999
    eng.store.update_payload(mid, m, status="RUNNING")
    monkeypatch.setattr("acero.portal.missions._POOL.submit", lambda fn: None)
    from acero.portal.missions import _ACTIVE, _LOCK
    with _LOCK:
        _ACTIVE.discard(mid)                  # que no lo dedupe

    eng._submit(mid)
    edad = _t.time() - float(eng.store.get(mid)["heartbeat_ts"])
    assert edad < 5                            # el latido quedó fresco al encolar
    with _LOCK:
        _ACTIVE.discard(mid)                  # limpieza para otros tests
