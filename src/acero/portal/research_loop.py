"""Principal Investigator (PI) loop — autonomous research director.

Decouples THINKING from COMPUTE. On each *tick* the agent (Codex→Claude) reads a
COMPACT digest of the project state (never the raw data — tokens, not gigabytes),
decides the next most informative move under ACERO's methodology, enqueues
missions, and goes DORMANT. The MACHINE then runs the experiments (Mission Engine
+ the jailed agentic runner) with NO agent context loaded. When the missions
finish — or a maximum interval elapses — the next tick fires. The feedback of one
tick is written to a file that the next tick reads: that is the loop.

Invariants (the methodology rules, not the agent):
  * Every action is validated here and gated downstream by the constitution
    (null controls, independent cross-check, novelty, validity/specificity
    floors). The PI cannot bypass them.
  * Nothing is ever promoted to a DISCOVERY without human review. The loop only
    proposes, runs and reviews — it never publishes.
  * Autonomy is unlimited until the researcher pauses it; a dry tick (no valid
    new work) backs off instead of burning tokens in a hot spin.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root

MAX_NEW_HYP_PER_TICK = int(os.environ.get("ACERO_PI_MAX_NEW_HYP", "4"))
DEFAULT_INTERVAL_SEC = int(os.environ.get("ACERO_PI_INTERVAL_SEC", "1800"))
DRY_BACKOFF_CAP_SEC = int(os.environ.get("ACERO_PI_BACKOFF_CAP_SEC", "7200"))
_ACTIONS = {"generate_and_run", "run_existing", "deepen", "pause"}
_TERMINAL = {"DONE", "FAILED"}

PI_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string",
                   "enum": ["generate_and_run", "run_existing", "deepen", "pause"]},
        "focus": {"type": "string"},          # direction for new hypotheses
        "n_new": {"type": "integer"},          # how many new hypotheses to spawn
        "reasoning": {"type": "string"},
    },
    "required": ["action", "reasoning"],
    "additionalProperties": False,
}


# --- loop state + feedback file (the "retro a un archivo") --------------------

def loop_root() -> Path:
    env = os.environ.get("ACERO_LOOP_ROOT", "").strip()
    return Path(env) if env else repo_root() / "research" / "loop"


def _loop_dir(pid: str) -> Path:
    d = loop_root() / pid
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_state(pid: str) -> dict[str, Any]:
    f = _loop_dir(pid) / "state.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"paused": False, "ticks": 0, "dry_streak": 0, "status": "idle",
            "started_at": None, "last_tick_at": None}


def save_state(pid: str, state: dict[str, Any]) -> None:
    (_loop_dir(pid) / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def pause(pid: str) -> dict[str, Any]:
    st = load_state(pid)
    st["paused"] = True
    st["status"] = "paused"
    save_state(pid, st)
    return st


def resume(pid: str) -> dict[str, Any]:
    st = load_state(pid)
    st["paused"] = False
    st["status"] = "running"
    save_state(pid, st)
    return st


def is_paused(pid: str) -> bool:
    return bool(load_state(pid).get("paused"))


def append_feedback(pid: str, record: dict[str, Any]) -> None:
    with (_loop_dir(pid) / "feedback.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def recent_feedback(pid: str, n: int = 5) -> list[dict[str, Any]]:
    f = _loop_dir(pid) / "feedback.jsonl"
    if not f.exists():
        return []
    lines = f.read_text(encoding="utf-8").splitlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            continue
    return out


# --- compact state digest (tokens, not gigabytes) ----------------------------

def _top_metric(res: dict[str, Any]) -> str:
    m = res.get("metrics") or {}
    for k, v in m.items():
        if isinstance(v, (int, float)):
            return f"{k}={v:.4g}"
    return ""


def build_digest(sf: Any, pid: str, *, recent: int = 8) -> dict[str, Any]:
    """A small, LLM-sized snapshot of where the research stands."""
    from ..ledger.service import ResearchLedger
    from .critic import CriticAgent
    from .hypothesis_flow import HypothesisFlow

    fl = HypothesisFlow(sf)
    store = fl.store
    proj = ResearchLedger(sf).get_project(pid)

    hyps = store.list_objects(pid, kind="candidate")
    by_status: dict[str, int] = {}
    for h in hyps:
        s = (h.get("status") or "?").upper()
        by_status[s] = by_status.get(s, 0) + 1

    exps = store.list_objects(pid, kind="experiment")
    exps = sorted(exps, key=lambda x: x.get("created_at") or "", reverse=True)
    verdicts: list[dict[str, Any]] = []
    anomalies: list[str] = []
    for e in exps[:recent]:
        res = e.get("result") or {}
        v = res.get("verdict")
        if not v:
            continue
        verdicts.append({"title": (e.get("title") or "")[:70], "verdict": v,
                         "metric": _top_metric(res)})
        for a in (res.get("anomalies") or [])[:2]:
            anomalies.append(str(a)[:160])

    try:
        rig = CriticAgent(sf).rigor_score(pid)
        rigor = {"resolved": rig.get("resolved"), "total": rig.get("total")}
    except Exception:  # noqa: BLE001
        rigor = {}

    return {
        "project": {"title": getattr(proj, "title", ""),
                    "domain": getattr(proj, "domain", "")},
        "hypotheses_by_status": by_status,
        "n_hypotheses": len(hyps),
        "recent_verdicts": verdicts,
        "open_anomalies": anomalies[:6],
        "rigor": rigor,
        "recent_decisions": [
            {"action": r.get("decision", {}).get("action"),
             "focus": r.get("decision", {}).get("focus", "")[:60]}
            for r in recent_feedback(pid, 4)],
    }


# --- the Principal Investigator -----------------------------------------------

_METHODOLOGY = (
    "Eres el INVESTIGADOR PRINCIPAL de ACERO dirigiendo una investigación autónoma. "
    "La META es DESCUBRIR conocimiento nuevo, no confirmar lo asentado. Decide el "
    "SIGUIENTE paso MÁS INFORMATIVO dado el estado. Reglas que NO puedes romper: los "
    "experimentos usan datos públicos reales con controles nulos y verificación "
    "cruzada independiente; nada se declara descubrimiento sin revisión humana; "
    "prefiere anomalías y ángulos poco explorados sobre re-testear lo conocido. "
    "Acciones: 'generate_and_run' (crea n_new hipótesis nuevas hacia 'focus' y corre "
    "misiones), 'run_existing' (corre lo aprobado pendiente sin crear más), 'deepen' "
    "(profundiza el rigor de lo ya corrido), 'pause' (no hay paso informativo ahora)."
)


class PrincipalInvestigator:
    def __init__(self, sf: Any, *, provider: Any = None, engine: Any = None,
                 hyps: Any = None, flow: Any = None) -> None:
        self._sf = sf
        self._provider = provider
        self._engine = engine
        self._hyps = hyps
        self._flow = flow

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        return CodexCliProvider(timeout_sec=220)

    def _engine_(self) -> Any:
        if self._engine is not None:
            return self._engine
        from .missions import MissionEngine
        return MissionEngine(self._sf)

    def _hyps_(self) -> Any:
        if self._hyps is not None:
            return self._hyps
        from .hypotheses import HypothesisService
        return HypothesisService(self._sf)

    def _flow_(self) -> Any:
        if self._flow is not None:
            return self._flow
        from .hypothesis_flow import HypothesisFlow
        return HypothesisFlow(self._sf)

    def decide(self, digest: dict[str, Any]) -> dict[str, Any]:
        prov = self._prov()
        if prov is not None and getattr(prov, "available", lambda: False)():
            try:
                from .playbook import brief
                prompt = (brief(700) + "\n\n---\n\n" + _METHODOLOGY
                          + "\n\nESTADO ACTUAL (JSON):\n"
                          + json.dumps(digest, ensure_ascii=False)[:3500]
                          + "\n\nDevuelve la decisión.")
                out = prov.complete_json(prompt, PI_DECISION_SCHEMA, temperature=0.3)
                if isinstance(out, dict) and out.get("action"):
                    return out
            except Exception:  # noqa: BLE001 - fall through to deterministic
                pass
        return self._deterministic(digest)

    @staticmethod
    def _deterministic(digest: dict[str, Any]) -> dict[str, Any]:
        """No-LLM fallback: keep the loop moving sensibly."""
        approved = digest.get("hypotheses_by_status", {}).get("APPROVED", 0)
        if approved == 0:
            return {"action": "generate_and_run", "focus": "", "n_new": 3,
                    "reasoning": "sin hipótesis aprobadas: generar un lote inicial"}
        if digest.get("open_anomalies"):
            return {"action": "generate_and_run", "focus": "explicar anomalías",
                    "n_new": 2, "reasoning": "hay anomalías abiertas que perseguir"}
        return {"action": "run_existing", "focus": "", "n_new": 0,
                "reasoning": "correr lo aprobado pendiente"}

    def _validate(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Enforce the cheap methodology bounds before acting."""
        action = str(decision.get("action") or "").strip()
        if action not in _ACTIONS:
            action = "run_existing"
        try:
            n_new = max(0, min(MAX_NEW_HYP_PER_TICK, int(decision.get("n_new") or 0)))
        except Exception:  # noqa: BLE001
            n_new = 0
        if action != "generate_and_run":
            n_new = 0                              # n_new only applies to generation
        elif n_new == 0:
            n_new = 2                              # generate implies at least some new
        return {"action": action, "n_new": n_new,
                "focus": str(decision.get("focus") or "")[:200],
                "reasoning": str(decision.get("reasoning") or "")[:300]}

    def _apply(self, pid: str, d: dict[str, Any]) -> dict[str, Any]:
        applied: dict[str, Any] = {"generated": 0, "approved": 0, "started": 0}
        if d["action"] == "pause":
            pause(pid)
            applied["paused"] = True
            return applied
        if d["action"] == "generate_and_run" and d["n_new"] > 0:
            g = self._hyps_().generate(pid, n=d["n_new"], use_ai=True, focus=d["focus"])
            created = g.get("created", []) if isinstance(g, dict) else []
            applied["generated"] = len(created)
            flow = self._flow_()
            for c in created:                     # autonomy: PI approves; methodology
                try:                               # still gates evidence downstream
                    flow.set_status(pid, c["id"], "APPROVED", "PI loop")
                    applied["approved"] += 1
                except Exception:  # noqa: BLE001
                    continue
        if d["action"] in {"generate_and_run", "run_existing", "deepen"}:
            r = self._engine_().start_all(pid, use_ai=True, sync=False)
            applied["started"] = len(r.get("started", [])) if isinstance(r, dict) else 0
        return applied

    def tick(self, pid: str) -> dict[str, Any]:
        digest = build_digest(self._sf, pid)
        decision = self._validate(self.decide(digest))
        applied = self._apply(pid, decision)
        dry = (applied.get("started", 0) == 0 and applied.get("generated", 0) == 0
               and not applied.get("paused"))
        st = load_state(pid)
        st["ticks"] = int(st.get("ticks", 0)) + 1
        st["last_tick_at"] = now_iso()
        st["started_at"] = st.get("started_at") or now_iso()
        st["dry_streak"] = (int(st.get("dry_streak", 0)) + 1) if dry else 0
        st["status"] = "paused" if applied.get("paused") else "running"
        save_state(pid, st)
        record = {"ts": now_iso(), "tick": st["ticks"], "decision": decision,
                  "applied": applied, "dry": dry,
                  "digest": {k: digest[k] for k in
                             ("hypotheses_by_status", "recent_verdicts", "rigor")
                             if k in digest}}
        append_feedback(pid, record)
        return record


# --- the driver: event + interval, unlimited until paused ---------------------

class ResearchLoop:
    def __init__(self, sf: Any, *, pi: PrincipalInvestigator | None = None) -> None:
        self._sf = sf
        self._pi = pi or PrincipalInvestigator(sf)

    def active_missions(self, pid: str) -> int:
        try:
            ms = self._pi._engine_().list_missions(pid)
        except Exception:  # noqa: BLE001
            return 0
        return sum(1 for m in ms if (m.get("status") or "").upper() not in _TERMINAL)

    def _wait_for_missions(self, pid: str, interval_sec: int, poll_sec: int,
                           sleeper: Any, clock: Any) -> None:
        deadline = clock() + interval_sec
        while clock() < deadline:
            if is_paused(pid) or self.active_missions(pid) == 0:
                return
            sleeper(poll_sec)

    def run(self, pid: str, *, interval_sec: int = DEFAULT_INTERVAL_SEC,
            poll_sec: int = 10, max_ticks: int | None = None, wait: bool = True,
            sleeper: Any = time.sleep, clock: Any = time.monotonic) -> dict[str, Any]:
        """Drive the loop until paused (or max_ticks, used by tests)."""
        st = load_state(pid)
        st["paused"] = False
        st["status"] = "running"
        save_state(pid, st)
        done = 0
        while True:
            if is_paused(pid):
                break
            record = self._pi.tick(pid)
            done += 1
            if record.get("applied", {}).get("paused"):
                break
            if max_ticks is not None and done >= max_ticks:
                break
            if wait:
                streak = int(load_state(pid).get("dry_streak", 0))
                wait_for = interval_sec if streak == 0 else min(
                    DRY_BACKOFF_CAP_SEC, interval_sec * (2 ** streak))
                self._wait_for_missions(pid, wait_for, poll_sec, sleeper, clock)
        return {"ticks": done, "state": load_state(pid)}

    def start_background(self, pid: str, **kw: Any) -> None:
        import threading
        threading.Thread(target=lambda: self.run(pid, **kw), daemon=True,
                         name=f"acero-pi-{pid[:8]}").start()
