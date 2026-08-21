"""Mission Engine — the autonomous research cycle, persistent across restarts.

A MISSION runs the full pipeline for ONE approved hypothesis with no human
clicks in between:

    investigate → experiments_propose → experiments_run → synthesize

Every step is CHECKPOINTED in the ledger (kind="mission") before and after it
runs, so a portal restart never loses work: `resume_pending()` picks up any
mission whose worker died (stale heartbeat) and continues FROM THE NEXT STEP.
Failures are honest: the failing step records its error and the mission ends
FAILED — it can be resumed/retried, never silently skipped.

What stays HUMAN by constitution: approving hypotheses (missions only run on
approved ones), adopting improved versions, approving conclusions/dossiers.
"""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger
from ..provenance.events import ProvenanceAction

STEPS = ["investigate", "experiments_propose", "recovery_check",
         "experiments_run", "synthesize", "rigor_loop"]
# relative weights → a smooth 0-100% (experiments_run is by far the longest).
# recovery_check pesa 0: es instantáneo e informativo (reporta si el MÉTODO tiene
# validación de recuperación en el dominio), no trabajo que cuente como avance.
STEP_WEIGHT = {"investigate": 12, "experiments_propose": 12, "recovery_check": 0,
               "experiments_run": 46, "synthesize": 10, "rigor_loop": 20}
def _max_missions() -> int:
    """Concurrent missions. Each spawns an INDEPENDENT ephemeral `codex exec`
    (no shared session), so real parallelism is bounded by CPU/RAM and the
    user's own Codex quota — not by the engine. Override with ACERO_MAX_MISSIONS.
    Default 4 (was 2); clamped to [1, 12] to stay friendly to API rate limits.
    """
    try:
        v = int(os.environ.get("ACERO_MAX_MISSIONS", "4"))
    except ValueError:
        v = 4
    return max(1, min(v, 12))


MAX_MISSIONS = _max_missions()       # concurrent missions (each spawns Codex work)
STALE_HEARTBEAT_SEC = 180.0          # worker-gone threshold → re-submit (resume)
REAP_HUNG_SEC = 3600.0               # worker sin latido 1h → dado por muerto (force-FAIL)
_WATCHDOG_MIN_INTERVAL = 30.0        # throttle lazy self-heal on dashboard reads

_POOL = ThreadPoolExecutor(max_workers=MAX_MISSIONS, thread_name_prefix="mission")
_ACTIVE: set[str] = set()
_LOCK = threading.Lock()
_LAST_WATCHDOG = [0.0]


def _now_ts() -> float:
    import time
    return time.time()


def _stale_action(status: str, heartbeat_ts: float, in_active: bool,
                  now: float) -> str | None:
    """Pure decision for the watchdog (testable without threads/DB):
      - RUNNING + worker gone (not in _ACTIVE) + stale heartbeat → 'resume'
      - RUNNING + worker present but hung far past grace       → 'reap'
      - otherwise                                              → None
    """
    if status != "RUNNING":
        return None
    age = now - float(heartbeat_ts or 0)
    if not in_active and age > STALE_HEARTBEAT_SEC:
        return "resume"
    if in_active and age > REAP_HUNG_SEC:
        return "reap"
    return None


class MissionEngine:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # --- lifecycle -----------------------------------------------------------
    def start(self, project_id: str, hyp_id: str, *, use_ai: bool = True,
              sync: bool = False, force: bool = False) -> dict[str, Any]:
        from .hypothesis_flow import HypothesisFlow
        h = HypothesisFlow(self._sf).store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        if (h.get("status") or "").upper() != "APPROVED":
            return {"ok": False,
                    "error": "las misiones solo corren sobre hipótesis APROBADAS"}
        # one live mission per hypothesis
        for m in self.list_missions(project_id):
            if m.get("hyp_id") == hyp_id and m.get("status") in ("PENDING", "RUNNING"):
                return {"ok": False, "error": f"ya hay una misión activa ({m['id']})",
                        "mission_id": m["id"]}
        # P4 — EVA internal gate: attack the hypothesis BEFORE spending experiments.
        # A fatal flaw (vague / reformulation / HARKing / confirm-only / trivial) blocks
        # the mission so no Codex is burned; the human can override with force=True.
        if use_ai and not force:
            from .epistemic_bridge import internal_eva
            gate = internal_eva(h, use_ai=use_ai)
            if not gate["proceed"]:
                return {"ok": False, "blocked_by_eva": True,
                        "blockers": gate["blockers"],
                        "error": ("EVA interno bloqueó la misión (arréglala o fuerza): "
                                  + "; ".join(gate["blockers"]))}
        mid = new_id("msn")
        rec = {"id": mid, "project_id": project_id, "hyp_id": hyp_id,
               "hyp_tag": h.get("tag", ""), "kind": "deep_investigation",
               "status": "PENDING", "use_ai": use_ai,
               "steps": [{"name": s, "status": "PENDING", "started_at": None,
                          "finished_at": None, "error": "", "info": ""}
                         for s in STEPS],
               "created_at": now_iso(), "heartbeat_ts": 0.0}
        self.store.put(project_id, "mission", mid, rec, status="PENDING",
                       actor="mission_engine",
                       summary=f"misión profunda para {h.get('tag')}")
        if sync:
            self._execute(mid)
        else:
            self._submit(mid)
        return {"ok": True, "mission_id": mid, "steps": STEPS}

    def start_all(self, project_id: str, *, use_ai: bool = True,
                  sync: bool = False) -> dict[str, Any]:
        from .hypothesis_flow import HypothesisFlow
        started: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for h in HypothesisFlow(self._sf).approved(project_id):
            r = self.start(project_id, h["id"], use_ai=use_ai, sync=sync)
            (started if r.get("ok") else skipped).append(
                {"hyp": h.get("tag"), **({"mission_id": r.get("mission_id")}
                                         if r.get("ok") else {"why": r.get("error")})})
        return {"ok": True, "started": started, "skipped": skipped}

    def _submit(self, mission_id: str) -> None:
        with _LOCK:
            if mission_id in _ACTIVE:
                return
            _ACTIVE.add(mission_id)

        def _run() -> None:
            try:
                self._execute(mission_id)
            finally:
                with _LOCK:
                    _ACTIVE.discard(mission_id)
        _POOL.submit(_run)

    # --- persistence helpers ---------------------------------------------------
    @staticmethod
    def _pct(m: dict[str, Any]) -> int:
        """Smooth 0-100% from step weights + the running step's sub-fraction."""
        total = sum(STEP_WEIGHT.values()) or 100
        acc = 0.0
        for s in m.get("steps", []):
            w = STEP_WEIGHT.get(s["name"], 25)
            if s["status"] == "DONE":
                acc += w
            elif s["status"] == "RUNNING":
                acc += w * float(s.get("sub_frac") or 0.0)
        if m.get("status") == "DONE":
            return 100
        return max(0, min(99, round(100 * acc / total)))

    def _save(self, m: dict[str, Any]) -> None:
        m["heartbeat_ts"] = _now_ts()
        m["progress_pct"] = self._pct(m)
        self.store.update_payload(m["id"], m, status=m["status"])

    def list_missions(self, project_id: str) -> list[dict[str, Any]]:
        self._maybe_watchdog()
        ms = self.store.list_objects(project_id, kind="mission")
        return sorted(ms, key=lambda x: x.get("created_at") or "", reverse=True)

    def _maybe_watchdog(self) -> None:
        """Throttled self-heal on dashboard reads (so no restart is needed)."""
        now = _now_ts()
        with _LOCK:
            if now - _LAST_WATCHDOG[0] < _WATCHDOG_MIN_INTERVAL:
                return
            _LAST_WATCHDOG[0] = now
        try:
            r = self.watchdog()
            if r.get("resumed") or r.get("reaped"):
                print(f"[missions.watchdog] resumed={r['resumed']} reaped={r['reaped']}")
        except Exception as exc:  # noqa: BLE001 - self-heal must never break a read
            # nunca romper la lectura del dashboard, pero JAMÁS en silencio: un
            # watchdog que muere calladito deja misiones zombis y nadie se entera
            print(f"[missions.watchdog] ERROR en el barrido: {exc!r}")

    def watchdog(self) -> dict[str, Any]:
        """Recover missions whose worker vanished (re-submit) or hung (force-FAIL),
        WITHOUT a portal restart. Safe to call often: `_submit` dedups on `_ACTIVE`,
        and DONE step checkpoints are preserved so a resume continues, never restarts.

        Un registro corrupto NO puede matar el barrido: cada misión se procesa en su
        propio try/except. (2026-08-21: una nota vieja guardada con kind='mission' y
        sin 'id' tumbaba TODO el watchdog con KeyError en cada barrido — 4 misiones
        zombis quedaron RUNNING 8 horas sin que nadie las recuperara ni avisara.)"""
        resumed: list[str] = []
        reaped: list[str] = []
        skipped_bad: list[str] = []
        now = _now_ts()
        for p in self.ledger.list_projects():
            try:
                missions = self.store.list_objects(p.id, kind="mission")
            except Exception:  # noqa: BLE001 - un proyecto roto no frena a los demás
                skipped_bad.append(f"project:{p.id}")
                continue
            for m in missions:
                try:
                    mid = m.get("id")
                    if not mid or not isinstance(m.get("steps"), list):
                        # no es una misión de verdad (nota/objeto ajeno con kind=mission)
                        skipped_bad.append(str(mid or m.get("titulo") or "?")[:40])
                        continue
                    action = _stale_action(m.get("status", ""),
                                           float(m.get("heartbeat_ts") or 0),
                                           mid in _ACTIVE, now)
                    if action == "resume":
                        self._submit(mid)
                        resumed.append(mid)
                    elif action == "reap":
                        for s in m.get("steps", []):
                            if s["status"] == "RUNNING":
                                s["status"] = "FAILED"
                                s["error"] = "worker colgado sin heartbeat (reaped); reintentable"
                                s["finished_at"] = now_iso()
                        m["status"] = "FAILED"
                        self._save(m)
                        reaped.append(mid)
                except Exception as exc:  # noqa: BLE001 - aislar registro por registro
                    skipped_bad.append(f"{m.get('id') or '?'}:{type(exc).__name__}")
        return {"ok": True, "resumed": resumed, "reaped": reaped,
                "skipped_bad": skipped_bad}

    def resume_pending(self, *, sync: bool = False) -> dict[str, Any]:
        """After a restart: re-launch PENDING missions and ALL RUNNING ones.

        Los workers viven DENTRO del proceso del portal: si este proceso acaba de
        nacer, NINGÚN worker puede seguir vivo — el heartbeat "fresco" de una misión
        RUNNING solo significa que el proceso anterior murió hace <60s, no que
        alguien la siga corriendo. (2026-08-21: confiar en el heartbeat aquí dejó 4
        misiones zombis 8 horas: el reinicio las mató a <3 min de su último latido y
        'las dejamos en paz' para siempre.) DONE checkpoints se conservan: retomar
        continúa, no repite."""
        resumed = []
        for p in self.ledger.list_projects():
            for m in self.list_missions(p.id):
                mid = m.get("id")
                if not mid or not isinstance(m.get("steps"), list):
                    continue                  # nota/objeto ajeno con kind=mission
                if m.get("status") in ("PENDING", "RUNNING"):
                    resumed.append(mid)
                    if sync:
                        self._execute(mid)
                    else:
                        self._submit(mid)
        return {"ok": True, "resumed": resumed}

    def retry(self, mission_id: str, *, sync: bool = False) -> dict[str, Any]:
        m = self.store.get(mission_id)
        if not m:
            return {"ok": False, "error": "mission not found"}
        if m.get("status") == "RUNNING" and \
                (_now_ts() - float(m.get("heartbeat_ts") or 0)) <= STALE_HEARTBEAT_SEC:
            return {"ok": False, "error": "la misión sigue viva"}
        # reset FAILED steps to PENDING (DONE checkpoints are kept)
        for s in m["steps"]:
            if s["status"] in ("FAILED", "RUNNING"):
                s["status"] = "PENDING"
                s["error"] = ""
        m["status"] = "PENDING"
        self._save(m)
        if sync:
            self._execute(mission_id)
        else:
            self._submit(mission_id)
        return {"ok": True, "mission_id": mission_id}

    # --- execution ----------------------------------------------------------------
    def _execute(self, mission_id: str) -> None:
        m = self.store.get(mission_id)
        if not m:
            return
        m["status"] = "RUNNING"
        self._save(m)
        # Keep-alive heartbeat: while this worker is alive, bump the mission's heartbeat
        # every 60s so a LONG-but-progressing step (the agent may legitimately take a
        # long time designing/running an experiment) is NOT falsely reaped. Only a truly
        # dead worker stops beating → reaped after REAP_HUNG_SEC. The real "hung" guard is
        # the per-call LLM timeout (ACERO_LLM_TIMEOUT).
        _stop_beat = threading.Event()

        def _beat() -> None:
            while not _stop_beat.wait(60):
                try:
                    self.store.update_payload(mission_id, {"heartbeat_ts": _now_ts()})
                except Exception:  # noqa: BLE001
                    pass
        _hb = threading.Thread(target=_beat, name=f"beat-{mission_id[:8]}", daemon=True)
        _hb.start()
        try:
            self._execute_steps(m)
        finally:
            _stop_beat.set()

    def _execute_steps(self, m: dict[str, Any]) -> None:
        for step in m["steps"]:
            if step["status"] == "DONE":
                continue                      # checkpoint: already done pre-restart
            step["status"] = "RUNNING"
            step["started_at"] = now_iso()
            step["sub_frac"] = 0.0
            self._save(m)
            try:
                info = self._run_step(m, step)
                step["status"] = "DONE"
                step["sub_frac"] = 1.0
                step["info"] = str(info)[:300]
            except Exception as exc:  # noqa: BLE001 - honest failure, resumable
                step["status"] = "FAILED"
                step["error"] = str(exc)[:300]
                step["finished_at"] = now_iso()
                m["status"] = "FAILED"
                self._save(m)
                self.ledger.record_event(
                    m["project_id"], ProvenanceAction.UPDATE, "mission_engine",
                    f"misión {m['id'][:12]} FALLÓ en {step['name']}"[:150],
                    {"step": step["name"]}, entity_id=m["id"])
                return
            step["finished_at"] = now_iso()
            self._save(m)
        m["status"] = "DONE"
        m["finished_at"] = now_iso()
        self._save(m)

    def _run_step(self, m: dict[str, Any], step: dict[str, Any]) -> str:
        from .hypothesis_flow import HypothesisFlow
        fl = HypothesisFlow(self._sf)
        pid, hid = m["project_id"], m["hyp_id"]
        use_ai = bool(m.get("use_ai", True))
        name = step["name"]

        if name == "investigate":
            step["sub"] = "buscando literatura real (multi-fuente)…"
            self._save(m)
            r = fl.investigate(pid, hid, use_ai=use_ai, via=f"mission:{m['id']}")
            if not r.get("ok"):
                raise RuntimeError(r.get("error", "investigate failed"))
            return f"{r.get('n_papers')} papers · " \
                   f"{(r.get('confrontation') or {}).get('stance','')}"

        if name == "recovery_check":
            # Reconexión 2026-08-21 (CCC-7): banco de recuperación — ¿el MÉTODO
            # puede recuperar una verdad conocida en este dominio? Paso
            # INFORMATIVO (peso 0): reporta la validación disponible, nunca
            # bloquea — correr los controles es decisión del humano/benchmark.
            from .recovery_bench import controls_for
            try:
                p = self.ledger.get_project(pid)
                domain = str(getattr(p, "domain", "") or "general")
            except Exception:  # noqa: BLE001
                domain = "general"
            ctr = controls_for(domain)
            if not ctr:
                return (f"dominio '{domain}' sin controles de recuperación "
                        "predefinidos — el banco (recovery_bench) no aplica aquí")
            return (f"{len(ctr)} control(es) de recuperación definidos para "
                    f"'{domain}' — sin corrida registrada en este proyecto; "
                    "correrlos calibra cuánta confianza merece el método")

        if name == "experiments_propose":
            existing = fl.experiments_for(pid, hid)
            if any(e.get("status") == "PROPOSED" for e in existing):
                return f"ya había {len(existing)} propuestos"
            step["sub"] = "Codex diseñando experimentos…"
            self._save(m)
            r = fl.propose_experiments(pid, hid, use_ai=use_ai, via=f"mission:{m['id']}")
            if not r.get("ok"):
                raise RuntimeError(r.get("error", "propose failed"))
            return f"{len(r.get('created', []))} experimentos propuestos"

        if name == "experiments_run":
            todo = [e for e in fl.experiments_for(pid, hid)
                    if e.get("status") == "PROPOSED"]
            total = len(todo)
            ran, modes = 0, []
            for i, e in enumerate(todo):
                step["sub"] = (f"corriendo experimento {i + 1}/{total}: "
                               f"{(e.get('title') or '')[:50]}")
                step["sub_frac"] = i / total if total else 0.0
                self._save(m)
                r = fl.run_experiment(pid, e["id"], use_ai=use_ai)
                ran += 1
                modes.append(r.get("mode", "?"))
                step["sub_frac"] = ran / total if total else 1.0
                self._save(m)
            return f"{ran} corridos ({', '.join(modes) or 'ninguno pendiente'})"

        if name == "synthesize":
            step["sub"] = "actualizando conocimiento y dossier…"
            self._save(m)
            from .synthesis import synthesize_hypothesis
            r = synthesize_hypothesis(pid, hid, self._sf, use_ai=use_ai)
            return r.get("summary", "síntesis registrada")[:200]

        if name == "rigor_loop":
            # AUTONOMOUS "machacar a Aristóteles": consult the critic, turn its
            # executable suggestions into experiments, run them, and re-synthesize
            # so it re-reviews its own objections against the new evidence.
            if not use_ai:
                return "omitido (offline)"
            from .critic import CriticAgent
            from .synthesis import synthesize_hypothesis
            ag = CriticAgent(self._sf)
            step["sub"] = "Aristóteles revisa y propone cómo reforzar…"
            self._save(m)
            ag.critique_now(pid, hid, "literatura",
                            f"Hipótesis: {(self.store.get(hid) or {}).get('title','')}. "
                            "Revisa el trabajo ejecutado y propón experimentos "
                            "concretos que refuercen o refuten con más rigor.",
                            use_ai=True)
            conv = ag.suggestions_to_experiments(pid, hid)
            new = conv.get("created", []) if conv.get("ok") else []
            ran = 0
            for e in new[:2]:            # bounded: at most 2 extra experiments
                step["sub"] = f"corriendo experimento de rigor: {e['title'][:45]}"
                step["sub_frac"] = ran / max(1, len(new[:2]))
                self._save(m)
                fl.run_experiment(pid, e["id"], use_ai=use_ai)
                ran += 1
            synthesize_hypothesis(pid, hid, self._sf, use_ai=use_ai)  # re-review
            rig = ag.rigor_score(pid)
            return (f"Aristóteles: {ran} experimentos de rigor corridos; "
                    f"objeciones resueltas {rig.get('resolved')}/{rig.get('total')}")

        raise RuntimeError(f"paso desconocido: {name}")


def resume_on_startup(delay_sec: float = 3.0) -> None:
    """Portal boot hook: resume interrupted missions in the background."""
    if os.environ.get("ACERO_MISSIONS_DISABLED") == "1":
        return

    def _later() -> None:
        import time
        time.sleep(delay_sec)
        try:
            MissionEngine().resume_pending()
        except Exception:  # noqa: BLE001 - resume must never block boot
            pass
    threading.Thread(target=_later, name="mission-resume", daemon=True).start()
