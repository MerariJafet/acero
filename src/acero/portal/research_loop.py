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

from collections import Counter

from ..core.clock import now_iso
from ..core.config import repo_root
from ..core.ids import new_id

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

SYNTHESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "synthesis": {"type": "string"},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "decision": {"type": "string", "enum": ["relaunch", "needs_human_review"]},
        "next_focus": {"type": "string"},
        "next_n": {"type": "integer"},
    },
    "required": ["synthesis", "decision"],
    "additionalProperties": False,
}

_SYNTHESIS_SYS = (
    "Eres Bohr, el orquestador del Consejo de ACERO. Se cumplió el temporizador de "
    "Modo Loop: el Investigador Principal corrió de forma autónoma durante horas "
    "sin supervisión humana. Tu trabajo ahora es el de un director que vuelve a la "
    "sala: escuchar TODO lo que pasó -- decisiones tomadas, veredictos, anomalías, "
    "bloqueos del gate EVA -- y (1) sintetizar honestamente qué se aprendió de "
    "verdad, sin inflar; (2) listar las preguntas que quedaron abiertas; (3) "
    "decidir si hay una dirección de siguiente lanzamiento clara y bien fundada, o "
    "si lo correcto es parar y pedir revisión humana. 'needs_human_review' es un "
    "cierre digno si nada maduró -- inflar el resultado es el único fracaso real."
)


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
            "started_at": None, "last_tick_at": None,
            "deadline": None, "deadline_hours": None, "last_synthesis_id": None}


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


def start_timed(pid: str, hours: float) -> dict[str, Any]:
    """Modo Loop: arranca el loop con un temporizador. Al cumplirse las `hours`,
    el driver (ResearchLoop.run) llama a synthesize_and_relaunch en vez de seguir
    tickeando indefinidamente — alguien del Consejo cierra el ciclo por su cuenta,
    sin que el humano tenga que volver a tocar nada."""
    st = resume(pid)
    hours = max(0.05, float(hours))
    st["deadline"] = time.time() + hours * 3600
    st["deadline_hours"] = hours
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
        # framings the EVA gate rejected recently — so the PI stops proposing them
        "eva_blocked": list({b for r in recent_feedback(pid, 4)
                             for b in (r.get("applied", {}).get("blocks") or [])})[:6],
    }


# --- the Principal Investigator -----------------------------------------------

_METHODOLOGY = (
    "Eres el INVESTIGADOR PRINCIPAL de ACERO dirigiendo una investigación autónoma. "
    "La META es DESCUBRIR conocimiento nuevo, no confirmar lo asentado. No se trata "
    "de usar una herramienta ya conocida de la forma ya conocida: se trata de "
    "COMBINAR las herramientas y personajes del Consejo entre sí, como piezas de "
    "lego, hasta encontrar una combinación que nadie ha probado y que abra algo "
    "nuevo. Decide el SIGUIENTE paso MÁS INFORMATIVO dado el estado. Reglas que NO "
    "puedes romper: los experimentos usan datos públicos reales con controles nulos "
    "y verificación cruzada independiente; nada se declara descubrimiento sin "
    "revisión humana; prefiere anomalías y ángulos poco explorados sobre re-testear "
    "lo conocido. "
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

    _ANTI_HARK = (" — formula PREDICCIONES A PRIORI, falsables y NO triviales, que "
                  "se prueben con datos INDEPENDIENTES (no derivadas de un resultado ya "
                  "visto); evita marcos post-hoc/HARKing y efectos triviales")

    def _proposed(self, pid: str) -> list[dict[str, Any]]:
        """Backlog de propuestas sin dictaminar, de más vieja a más nueva.
        Defensivo: un flow sin store (fakes de test) cuenta como backlog vacío."""
        try:
            rows = [h for h in self._flow_().store.list_objects(pid, kind="candidate")
                    if h.get("id") and (h.get("status") or "").upper() == "PROPOSED"]
        except Exception:  # noqa: BLE001
            return []
        return sorted(rows, key=lambda h: str(h.get("created_at") or h.get("id") or ""))

    def _question_seed(self, pid: str, focus: str) -> str:
        """Reconexión 2026-08-21 (EP3/F4): los bloqueos EVA recientes SON
        vulnerabilidades epistémicas detectadas; el motor de preguntas las
        convierte en preguntas fértiles (gateadas por calidad) que guían la
        SIGUIENTE generación — el fracaso de ayer se vuelve la pregunta de hoy.
        Antes el question_engine existía y nadie lo llamaba desde el flujo vivo."""
        try:
            blocks: list[str] = []
            for r in recent_feedback(pid, 6):
                for b in (r.get("applied") or {}).get("blocks") or []:
                    s = str(b).strip()
                    # los "misión activa" son de concurrencia, no epistémicos
                    if s and "misión activa" not in s and s not in blocks:
                        blocks.append(s)
            if not blocks:
                return focus
            from ..epistemic.claim_reconstructor import ClaimRecord
            from ..epistemic.vulnerability import (EpistemicVulnerability,
                                                   VulnerabilityType)
            from ..questions.question_engine import generate_portfolio
            claim = ClaimRecord(
                claim_id=pid,
                claim_text=(focus or "las hipótesis del proyecto")[:200])
            vulns = [EpistemicVulnerability(
                vulnerability_id=f"evablk-{i}", target_claim=claim.claim_text,
                type=VulnerabilityType.UNVALIDATED_ASSUMPTION,
                description=b[:200]) for i, b in enumerate(blocks[:5])]
            top = [r.question.question_text
                   for r in generate_portfolio(vulns, claim)[:3] if r.priority > 0]
            if top:
                return (focus + " | PREGUNTAS FÉRTILES (motor de preguntas, "
                        "derivadas de los bloqueos EVA recientes): "
                        + "; ".join(t[:140] for t in top))
        except Exception:  # noqa: BLE001 - la semilla nunca rompe la generación
            pass
        return focus

    def _dictamen_prov(self) -> Any:
        """Provider para el juicio de Bohr; None ⇒ dictamen determinístico."""
        if self._provider is not None:
            return self._provider
        try:
            return self._prov()
        except Exception:  # noqa: BLE001
            return None

    def _triage(self, pid: str, applied: dict[str, Any]) -> None:
        """Dictamen del backlog — el juicio es de BOHR, el orquestador: él dirige,
        él decide qué propuesta promete y cuál no (bohr.dictamen_backlog: el LLM
        rankea con razones, la máquina acota). NADIE más adjudica las propuestas
        que dejan sus ciclos, la máquina de anomalías, etc. — sin esto se acumulan
        PROPOSED para siempre (2026-08-21: 77 en un proyecto, tags duplicados) y
        el riel se llena de columnas que jamás avanzan. Reversible por el humano
        (botón restaurar):
          1) duplicadas (mismo claim normalizado) → REJECTED, se queda la original;
          2) si el backlog supera ACERO_PI_MAX_PROPOSED (def. 15), Bohr rankea y
             las que queden fuera del tope → REJECTED con su razón."""
        try:
            cap = max(1, int(os.environ.get("ACERO_PI_MAX_PROPOSED", "15")))
        except ValueError:
            cap = 15
        flow = self._flow_()
        pool = self._proposed(pid)
        seen: dict[str, str] = {}
        kept: list[dict[str, Any]] = []
        for h in pool:                              # 1) dedup — la original se queda
            key = " ".join(str(h.get("claim") or h.get("title") or "").lower().split())
            if key and key in seen:
                flow.set_status(pid, h["id"], "REJECTED",
                                f"Bohr (triaje): duplicada de {seen[key]}",
                                actor="bohr")
                applied["triaged_dup"] = applied.get("triaged_dup", 0) + 1
                continue
            if key:
                seen[key] = str(h.get("tag") or h["id"])
            kept.append(h)
        if len(kept) <= cap:
            return
        from ..science.bohr import dictamen_backlog     # 2) el juicio de Bohr
        d = dictamen_backlog(kept, cap, provider=self._dictamen_prov())
        drop = d["ranked"][cap:]
        for hid in drop:
            why = d["reasons"].get(hid) or ("desplazada por candidatas más "
                                            "prometedoras según su dictamen")
            flow.set_status(pid, hid, "REJECTED",
                            f"Bohr (triaje): {why} — restaurable", actor="bohr")
            applied["triaged_stale"] = applied.get("triaged_stale", 0) + 1

    def _generate_and_approve(self, pid: str, n: int, focus: str,
                              applied: dict[str, Any]) -> None:
        # ADOPTAR antes que inventar: si ya hay propuestas dictaminables en el
        # backlog (del Consejo, de anomalías…), Bohr rankea y el PI aprueba las
        # MEJORES según su dictamen en vez de generar candidatas nuevas encima —
        # así las H existentes AVANZAN y el backlog baja. Solo genera lo que
        # falte para completar n.
        flow = self._flow_()
        pool = self._proposed(pid)
        if pool and n > 0:
            from ..science.bohr import dictamen_backlog
            d = dictamen_backlog(pool, n, provider=self._dictamen_prov())
            for hid in d["ranked"][:max(0, n)]:
                try:
                    flow.set_status(pid, hid, "APPROVED",
                                    "Bohr: adoptada del backlog (dictamen)",
                                    actor="bohr")
                    applied["approved"] += 1
                    applied["adopted"] = applied.get("adopted", 0) + 1
                    n -= 1
                except Exception:  # noqa: BLE001
                    continue
        if n <= 0:
            return
        # Steer generation to pass the EVA gate (anti-HARKing / non-trivial) instead
        # of forcing past it — the methodology gate stays sovereign.
        focus = self._question_seed(pid, focus)
        g = self._hyps_().generate(pid, n=n, use_ai=True, focus=(focus + self._ANTI_HARK))
        created = g.get("created", []) if isinstance(g, dict) else []
        applied["generated"] += len(created)
        for c in created:                          # autonomy: PI approves; methodology
            try:                                    # still gates evidence downstream
                flow.set_status(pid, c["id"], "APPROVED", "PI loop")
                applied["approved"] += 1
            except Exception:  # noqa: BLE001
                continue

    def _deepen(self, pid: str, applied: dict[str, Any]) -> int:
        """Literatura de nivel 2 sobre las hipótesis aprobadas: indexa las
        REFERENCIAS de los papers ya leídos. Devuelve cuántas profundizó."""
        flow = self._flow_()
        n = 0
        try:
            approved = flow.approved(pid)
        except Exception:  # noqa: BLE001
            return 0
        for h in approved[:3]:              # techo por ronda: no quemar la API
            try:
                r = flow.deepen_literature(pid, h["id"])
                if isinstance(r, dict) and r.get("ok"):
                    n += 1
                elif isinstance(r, dict) and r.get("error"):
                    applied.setdefault("blocks", []).append(
                        f"deepen {h.get('tag', '')}: {str(r['error'])[:120]}")
            except Exception as exc:  # noqa: BLE001 - una hipótesis rota no frena
                applied.setdefault("blocks", []).append(
                    f"deepen falló: {str(exc)[:120]}")
        return n

    def _start(self, pid: str) -> tuple[int, list[str]]:
        """Start missions for approved hypotheses. Returns (n_started, block_reasons).
        Hypotheses the EVA gate rejects (HARKing/trivial/vague) come back as skips —
        we surface those reasons so the next generation can avoid them. We do NOT
        force past EVA: the methodology gate stays sovereign."""
        r = self._engine_().start_all(pid, use_ai=True, sync=False)
        if not isinstance(r, dict):
            return 0, []
        started = len(r.get("started", []))
        blocks = [str(s.get("why") or "")[:160] for s in r.get("skipped", [])
                  if s.get("why")]
        return started, blocks

    def _apply(self, pid: str, d: dict[str, Any]) -> dict[str, Any]:
        applied: dict[str, Any] = {"generated": 0, "approved": 0, "started": 0,
                                   "blocks": []}
        # El dictamen del backlog corre SIEMPRE (también en cooldown): no gasta
        # cómputo científico, solo adjudica lo que nadie más adjudica.
        try:
            self._triage(pid, applied)
        except Exception:  # noqa: BLE001 - el triaje nunca tumba el tick
            pass
        if d["action"] == "pause":
            # The PI signalling "no productive step now" must NOT stop the loop —
            # autonomy is unlimited until the RESEARCHER pauses. Treat it as a
            # COOLDOWN: add no work, let the in-flight missions drain, back off, and
            # re-tick once the state has changed (concurrency eased, verdicts in).
            applied["cooldown"] = True
            applied["reason"] = str(d.get("reasoning") or "")[:200]
            return applied
        if d["action"] == "deepen":
            # 'deepen' hacía EXACTAMENTE lo mismo que 'run_existing' (ambas solo
            # llamaban a _start), así que el PI podía "decidir" distinto sin que
            # cambiara nada — de ahí el BUCLE_DE_DECISION que vio el Auditor el
            # 2026-08-21. deepen_literature() existía y nadie la llamaba: ahora
            # profundizar significa leer las REFERENCIAS de lo ya leído. Bonus:
            # la literatura NO usa el agente de codegen, así que sigue
            # produciendo trabajo real aunque la fábrica esté caída.
            applied["deepened"] = self._deepen(pid, applied)
        if d["action"] == "generate_and_run" and d["n_new"] > 0:
            self._generate_and_approve(pid, d["n_new"], d["focus"], applied)
        started, blocks = self._start(pid)
        # += y no =: sobrescribir borraba los motivos que ya había anotado
        # _deepen ("sin papers indexados"…), y esos motivos son justo lo que
        # explica por qué una ronda no produjo nada.
        applied["started"] = started
        applied["blocks"] = list(applied.get("blocks") or []) + list(blocks)
        # Self-correct: if the chosen action found NOTHING runnable (no approved
        # hypotheses, or every mission already finished), EXPAND THE FRONTIER with
        # new hypotheses instead of spinning dry. Methodology says: nothing to run
        # ⇒ explore. (If the fresh hypotheses are EVA-blocked, `started` stays 0 and
        # the tick counts as dry → the driver backs off; it will NOT hot-spin.)
        if started == 0 and applied["generated"] == 0:
            self._generate_and_approve(pid, max(2, d.get("n_new", 0) or 2),
                                       d.get("focus", ""), applied)
            applied["expanded"] = True
            applied["started"], b2 = self._start(pid)
            applied["blocks"] += b2
        return applied

    def tick(self, pid: str) -> dict[str, Any]:
        digest = build_digest(self._sf, pid)
        decision = self._validate(self.decide(digest))
        applied = self._apply(pid, decision)
        # dry = nothing actually RAN. Generating hypotheses that the EVA gate then
        # blocks is NOT progress — so the driver backs off instead of hot-spinning
        # on generation+EVA calls that never launch an experiment.
        dry = applied.get("started", 0) == 0 and not applied.get("paused")
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


def _deterministic_synthesis(digest: dict[str, Any], n_ticks: int) -> dict[str, Any]:
    """Fallback sin LLM: mecánico, honesto, nunca infla."""
    rigor = digest.get("rigor") or {}
    anomalies = digest.get("open_anomalies") or []
    by_status = digest.get("hypotheses_by_status") or {}
    parts = [f"{n_ticks} ticks corridos.", f"hipótesis por estado: {by_status}."]
    if rigor:
        parts.append(f"rigor: {rigor.get('resolved', 0)}/{rigor.get('total', 0)} resuelto.")
    if anomalies:
        parts.append(f"{len(anomalies)} anomalía(s) abierta(s) sin perseguir.")
    if anomalies:
        return {"synthesis": " ".join(parts), "open_questions": anomalies[:5],
                "decision": "relaunch", "next_focus": "explicar anomalías abiertas",
                "next_n": 2}
    return {"synthesis": " ".join(parts), "open_questions": anomalies[:5],
            "decision": "needs_human_review", "next_focus": "", "next_n": 0}


def synthesize_and_relaunch(sf: Any, pid: str, *, provider: Any = None,
                            pi: PrincipalInvestigator | None = None) -> dict[str, Any]:
    """Al cumplirse el temporizador de Modo Loop, alguien del Consejo (Bohr) toma el
    control: sintetiza todo lo ocurrido, escucha las preguntas abiertas, y decide si
    hay una dirección clara de siguiente lanzamiento -- y si la hay, la lanza él
    mismo. Se registra siempre al ledger, se decida lo que se decida: 'inflar' no es
    una opción, 'needs_human_review' es un cierre digno."""
    pi = pi or PrincipalInvestigator(sf, provider=provider)
    digest = build_digest(sf, pid, recent=20)
    fb = recent_feedback(pid, 200)
    st = load_state(pid)
    n_ticks = len(fb)
    all_blocks = sorted({b for r in fb for b in (r.get("applied", {}).get("blocks") or [])})
    action_counts = dict(Counter(
        r.get("decision", {}).get("action") for r in fb if r.get("decision")))

    prov = provider if provider is not None else pi._prov()
    decision: dict[str, Any] = _deterministic_synthesis(digest, n_ticks)
    if prov is not None and getattr(prov, "available", lambda: False)():
        try:
            from .playbook import brief
            prompt = (
                brief(700) + "\n\n---\n\n" + _SYNTHESIS_SYS
                + "\n\nRESUMEN DE LA VENTANA DE MODO LOOP (JSON):\n"
                + json.dumps({
                    "horas_corridas": st.get("deadline_hours"),
                    "n_ticks": n_ticks,
                    "acciones_por_tipo": action_counts,
                    "bloqueos_eva_recientes": all_blocks[:10],
                    "digest_actual": digest,
                }, ensure_ascii=False)[:4500]
                + "\n\nDevuelve la síntesis.")
            out = prov.complete_json(prompt, SYNTHESIS_SCHEMA, temperature=0.3)
            if isinstance(out, dict) and out.get("synthesis"):
                decision = out
        except Exception:  # noqa: BLE001 - keep the deterministic fallback
            pass

    if decision.get("decision") not in ("relaunch", "needs_human_review"):
        decision["decision"] = "needs_human_review"

    relaunched: dict[str, Any] = {"generated": 0, "approved": 0, "started": 0}
    if decision["decision"] == "relaunch":
        focus = str(decision.get("next_focus") or "")[:200]
        n = max(1, min(MAX_NEW_HYP_PER_TICK, int(decision.get("next_n") or 2)))
        pi._generate_and_approve(pid, n, focus, relaunched)
        started, blocks = pi._start(pid)
        relaunched["started"] = started
        relaunched["blocks"] = blocks

    record = {
        "id": new_id("syn"),
        "ts": now_iso(),
        "hours": st.get("deadline_hours"),
        "n_ticks": n_ticks,
        "synthesis": decision.get("synthesis", ""),
        "open_questions": decision.get("open_questions") or [],
        "decision": decision["decision"],
        "next_focus": decision.get("next_focus", ""),
        "relaunched": relaunched,
    }
    try:
        from ..discovery.store import DiscoveryStore
        from ..ledger.service import ResearchLedger
        store = DiscoveryStore(sf, ResearchLedger(sf))
        store.put(pid, "report", record["id"], record, status="RECORDED",
                  actor="bohr_modo_loop",
                  summary=f"Síntesis de Modo Loop ({st.get('deadline_hours')}h, "
                          f"{n_ticks} ticks) -> {decision['decision']}")
    except Exception:  # noqa: BLE001
        pass  # la síntesis igual queda en el estado/feedback del loop

    st["paused"] = True
    st["status"] = "modo_loop_completed"
    st["deadline"] = None
    st["last_synthesis_id"] = record["id"]
    save_state(pid, st)
    append_feedback(pid, {"ts": now_iso(), "tick": st.get("ticks", 0),
                          "modo_loop_synthesis": record})
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
            deadline = load_state(pid).get("deadline")
            if deadline is not None and time.time() >= float(deadline):
                # Modo Loop: el temporizador se cumplió. Alguien del Consejo (Bohr)
                # sintetiza todo lo corrido y decide el siguiente lanzamiento por su
                # cuenta -- el humano no tiene que volver a tocar nada para que el
                # ciclo se cierre con una decisión, no en silencio.
                synthesize_and_relaunch(self._sf, pid)
                break
            self._pi.tick(pid)          # state + feedback are persisted inside tick
            done += 1
            # NOTE: a PI 'pause'/cooldown decision does NOT break the loop — only the
            # researcher's pause (is_paused, checked at the top) stops it. The PI can
            # only decline to add work; the loop keeps cycling until the human pauses.
            if max_ticks is not None and done >= max_ticks:
                break
            if wait:
                st_wait = load_state(pid)
                streak = int(st_wait.get("dry_streak", 0))
                wait_for = interval_sec if streak == 0 else min(
                    DRY_BACKOFF_CAP_SEC, interval_sec * (2 ** streak))
                deadline = st_wait.get("deadline")
                if deadline is not None:
                    # No dormir MÁS ALLÁ del temporizador de Modo Loop -- si no, la
                    # síntesis se dispara hasta interval_sec tarde.
                    wait_for = max(1, min(wait_for, int(float(deadline) - time.time())))
                self._wait_for_missions(pid, wait_for, poll_sec, sleeper, clock)
        return {"ticks": done, "state": load_state(pid)}

    def start_background(self, pid: str, **kw: Any) -> None:
        import threading
        threading.Thread(target=lambda: self.run(pid, **kw), daemon=True,
                         name=f"acero-pi-{pid[:8]}").start()


# --- convenience builders (portal endpoints) ----------------------------------

def _default_sf() -> Any:
    from ..ledger.db import default_session_factory
    return default_session_factory()


def default_pi() -> PrincipalInvestigator:
    return PrincipalInvestigator(_default_sf())


def default_loop() -> ResearchLoop:
    return ResearchLoop(_default_sf())


def resume_on_startup(delay_sec: float = 3.0) -> None:
    """Portal boot hook: el Centinela (PI) corre como hilo EN EL PROCESO del
    portal -- si el portal se reinicia, el hilo muere aunque el state.json
    siga diciendo 'running'. Sin esto, cada reinicio dejaba proyectos
    marcados como corriendo pero en silencio hasta que alguien volviera a
    tocar el botón. Aquí se revive solo lo que estaba realmente activo."""
    if os.environ.get("ACERO_PI_RESUME_DISABLED") == "1":
        return

    def _later() -> None:
        time.sleep(delay_sec)
        root = loop_root()
        if not root.exists():
            return
        loop = default_loop()
        for d in root.iterdir():
            if not d.is_dir():
                continue
            pid = d.name
            try:
                st = load_state(pid)
                if st.get("paused") or st.get("status") != "running":
                    continue
                loop.start_background(pid)
            except Exception:  # noqa: BLE001 - one broken project must not block the rest
                continue

    import threading
    threading.Thread(target=_later, name="pi-resume", daemon=True).start()
