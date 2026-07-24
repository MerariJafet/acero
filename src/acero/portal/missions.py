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

STEPS = ["investigate", "experiments_propose", "experiments_run", "synthesize",
         "rigor_loop"]
# relative weights → a smooth 0-100% (experiments_run is by far the longest)
STEP_WEIGHT = {"investigate": 12, "experiments_propose": 12,
               "experiments_run": 46, "synthesize": 10, "rigor_loop": 20}
MAX_MISSIONS = 2                     # concurrent missions (each spawns Codex work)
STALE_HEARTBEAT_SEC = 180.0

_POOL = ThreadPoolExecutor(max_workers=MAX_MISSIONS, thread_name_prefix="mission")
_ACTIVE: set[str] = set()
_LOCK = threading.Lock()


def _now_ts() -> float:
    import time
    return time.time()


class MissionEngine:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # --- lifecycle -----------------------------------------------------------
    def start(self, project_id: str, hyp_id: str, *, use_ai: bool = True,
              sync: bool = False) -> dict[str, Any]:
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
        ms = self.store.list_objects(project_id, kind="mission")
        return sorted(ms, key=lambda x: x.get("created_at") or "", reverse=True)

    def resume_pending(self, *, sync: bool = False) -> dict[str, Any]:
        """After a restart: re-launch PENDING missions and RUNNING ones whose
        worker died (stale heartbeat). Live ones (fresh heartbeat) are left alone."""
        resumed = []
        for p in self.ledger.list_projects():
            for m in self.list_missions(p.id):
                st = m.get("status")
                stale = (_now_ts() - float(m.get("heartbeat_ts") or 0)
                         ) > STALE_HEARTBEAT_SEC
                if st == "PENDING" or (st == "RUNNING" and stale):
                    resumed.append(m["id"])
                    if sync:
                        self._execute(m["id"])
                    else:
                        self._submit(m["id"])
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
                    f"misión {mission_id[:12]} FALLÓ en {step['name']}"[:150],
                    {"step": step["name"]}, entity_id=mission_id)
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
