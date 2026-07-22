"""El Revisor — resident critical-researcher subagent.

After every research task (hypotheses generated, literature confronted, version
adopted, experiments proposed/run) this agent activates in the background, reads
the project's REAL literature (stored abstracts), and issues a structured critique
from the persona defined in critic_soul.md. Critiques persist (kind="critique")
and render as a footer on each card, so the human always has an adversarial
second opinion.

Epistemic status: the critic is an LLM aid — its output is a REVIEW PROMPT for the
human, never evidence and never a verdict of record. It runs on local Codex CLI.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

_SOUL = (Path(__file__).parent / "critic_soul.md").read_text(encoding="utf-8")

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},          # solido|prometedor|debil|defectuoso
        "summary": {"type": "string"},          # 2-3 frases, lo esencial
        "objections": {"type": "array", "items": {"type": "string"}},
        "alternatives": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
        "hard_question": {"type": "string"},    # la pregunta más incómoda
    },
    "required": ["verdict", "summary", "objections", "alternatives",
                 "suggestions", "hard_question"],
    "additionalProperties": False,
}

_TASK_LABEL = {
    "hipotesis": "una HIPÓTESIS recién propuesta",
    "literatura": "una CONFRONTACIÓN de hipótesis contra literatura real",
    "nueva_version": "la ADOPCIÓN de una versión mejorada de una hipótesis",
    "experimento_propuesto": "un EXPERIMENTO propuesto (aún no ejecutado)",
    "experimento_resultado": "el RESULTADO/PLAN de un experimento ejecutado",
}

# one shared pool: the critic must never stampede Codex nor block the flow
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="critic")
_LOCK = threading.Lock()


class CriticAgent:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # --- context: the critic reads the project's REAL literature -------------
    def _literature_context(self, project_id: str, limit: int = 6) -> str:
        lit = self.store.list_objects(project_id, kind="literature")
        # prefer papers WITH abstracts, most relevant first
        lit = sorted((p for p in lit if p.get("abstract")),
                     key=lambda p: p.get("relevance") or 0, reverse=True)[:limit]
        if not lit:
            return "(el proyecto aún no tiene literatura indexada con abstracts)"
        return "\n".join(
            f"- «{p.get('title','')}» [{p.get('source','')}]: "
            f"{(p.get('abstract') or '')[:350]}"
            for p in lit)

    # --- synchronous critique (used directly in tests) ------------------------
    def _version_label(self, project_id: str, target_id: str) -> tuple[int, str]:
        """Aris v{hypVersion}.{seq}: which version of the flow this critique judges."""
        t = self.store.get(target_id) or {}
        hyp = t if "tag" in t and "hyp_id" not in t else \
            (self.store.get(t.get("hyp_id", "")) or {})
        ver = int(hyp.get("version", 1)) if hyp else 1
        seq = 1 + sum(1 for x in self.store.list_objects(project_id, kind="critique")
                      if x.get("target_id") == target_id
                      and int(x.get("hyp_version", 1)) == ver)
        return ver, f"Aris v{ver}.{seq}"

    def critique_now(self, project_id: str, target_id: str, task: str,
                     context: str, *, use_ai: bool = True) -> dict[str, Any]:
        out = self._review(project_id, task, context, use_ai=use_ai)
        ver, label = self._version_label(project_id, target_id)
        rec = {"id": new_id("crit"), "target_id": target_id, "task": task,
               "hyp_version": ver, "label": label,
               "created_at": now_iso(), **out}
        self.store.put(project_id, "critique", rec["id"], rec, status="ISSUED",
                       actor="critic_agent",
                       summary=f"crítica ({task}): {out.get('verdict','')}")
        return rec

    def _review(self, project_id: str, task: str, context: str, *, use_ai: bool
                ) -> dict[str, Any]:
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=180)
                if prov.available():
                    lit = self._literature_context(project_id)
                    prompt = (
                        f"{_SOUL}\n\n---\n\n"
                        f"Vas a revisar {_TASK_LABEL.get(task, 'una tarea de investigación')} "
                        "de tu equipo.\n\n"
                        f"LITERATURA REAL del proyecto (abstracts verificados):\n{lit}\n\n"
                        f"TRABAJO A REVISAR:\n{context[:3500]}\n\n"
                        "Aplica tu método completo (afirmación exacta, falsación, "
                        "alternativas, literatura faltante, poder discriminante, revisor "
                        "hostil). Devuelve: verdict (solido|prometedor|debil|defectuoso), "
                        "summary, objections (2-4 concretas), alternatives (explicaciones "
                        "alternativas no descartadas), suggestions (ejecutables en la "
                        "compu), hard_question. NO inventes citas.")
                    out = prov.complete_json(prompt, CRITIC_SCHEMA, temperature=0.4)
                    return {"provider": "codex",
                            "verdict": out.get("verdict", ""),
                            "summary": out.get("summary", ""),
                            "objections": out.get("objections", [])[:4],
                            "alternatives": out.get("alternatives", [])[:3],
                            "suggestions": out.get("suggestions", [])[:3],
                            "hard_question": out.get("hard_question", "")}
            except Exception:  # noqa: BLE001
                pass
        # honest deterministic fallback — a checklist, clearly not an AI review
        return {"provider": "none", "verdict": "sin_revision",
                "summary": ("Revisor IA no disponible. Checklist mínimo: ¿qué falsaría "
                            "esto? ¿qué explicación alternativa (sesgo/artefacto/azar) "
                            "no se ha descartado? ¿qué paper incómodo falta?"),
                "objections": [], "alternatives": [], "suggestions": [],
                "hard_question": "¿Buscaste evidencia en contra con la misma energía "
                                 "que a favor?"}

    # --- C3: close the loop ------------------------------------------------------
    def suggestions_to_experiments(self, project_id: str, hyp_id: str
                                   ) -> dict[str, Any]:
        """Turn the critic's executable suggestions into PROPOSED experiments."""
        crit = self.latest_by_target(project_id).get(hyp_id)
        if not crit or not crit.get("suggestions"):
            return {"ok": False, "error": "no hay sugerencias del Revisor para convertir"}
        h = self.store.get(hyp_id) or {}
        created = []
        for s in crit["suggestions"][:3]:
            eid = new_id("exp")
            rec = {"id": eid, "hyp_id": hyp_id, "hyp_tag": h.get("tag", ""),
                   "title": f"[Revisor] {str(s)[:90]}",
                   "what": f"Responder la objeción del Revisor: {str(s)[:200]}",
                   "how": str(s), "data_source": "según sugerencia",
                   "method_type": "math_analysis",
                   "controls": "los que exige la sugerencia",
                   "discriminator": "resuelve o no la objeción planteada",
                   "from_critique": crit.get("id", ""),
                   "status": "PROPOSED", "synthetic": None, "created_at": now_iso()}
            self.store.put(project_id, "experiment", eid, rec, status="PROPOSED",
                           actor="critic_agent",
                           summary=f"experimento desde crítica para {h.get('tag')}")
            created.append(rec)
        return {"ok": True, "created": created, "critique_id": crit.get("id", "")}

    def resolve_objections(self, project_id: str, hyp_id: str, *,
                           use_ai: bool = True) -> dict[str, Any]:
        """Re-review: given the NEW evidence, which objections stand resolved?"""
        crit = self.latest_by_target(project_id).get(hyp_id)
        if not crit or not crit.get("objections"):
            return {"ok": True, "resolved": 0, "pending": 0, "note": "sin objeciones"}
        objections = list(crit["objections"])
        exps = [e for e in self.store.list_objects(project_id, kind="experiment")
                if e.get("hyp_id") == hyp_id and e.get("status") == "COMPLETE"]
        evidence = "\n".join(
            f"- {e.get('title','')}: {(e.get('result') or {}).get('verdict','')} — "
            f"{((e.get('result') or {}).get('verdict_reason') or '')[:180]}"
            for e in exps) or "(sin experimentos completados)"
        # keep previous resolutions: an objection resolved with evidence STAYS resolved
        prev = list(crit.get("objections_status") or [])
        statuses = [(prev[i] if i < len(prev) and prev[i] == "resolved" else "pending")
                    for i in range(len(objections))]
        if use_ai and exps:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=150)
                if prov.available():
                    schema = {"type": "object", "properties": {
                        "resolutions": {"type": "array", "items": {
                            "type": "object", "properties": {
                                "idx": {"type": "integer"},
                                "status": {"type": "string"},
                                "why": {"type": "string"}},
                            "required": ["idx", "status", "why"],
                            "additionalProperties": False}}},
                        "required": ["resolutions"], "additionalProperties": False}
                    objs = "\n".join(f"[{i}] {o}" for i, o in enumerate(objections))
                    out = prov.complete_json(
                        "Eres El Revisor. Estas eran TUS objeciones:\n" + objs +
                        f"\n\nEvidencia NUEVA ejecutada:\n{evidence}\n\n"
                        "Para cada objeción: status resolved SOLO si la evidencia la "
                        "responde de verdad, si no pending. Sé duro: en la duda, "
                        "pending. En español.", schema, temperature=0.2)
                    for r in out.get("resolutions", []):
                        i = int(r.get("idx", -1))
                        if 0 <= i < len(statuses) and r.get("status") == "resolved":
                            statuses[i] = "resolved"
            except Exception:  # noqa: BLE001
                pass
        self.store.update_payload(crit["id"], {
            "objections_status": statuses,
            "resolved_count": statuses.count("resolved"),
            "re_reviewed_at": now_iso()})
        return {"ok": True, "resolved": statuses.count("resolved"),
                "pending": statuses.count("pending"), "statuses": statuses}

    def rigor_score(self, project_id: str) -> dict[str, Any]:
        """Project rigor: objections resolved WITH EVIDENCE / total objections."""
        total = resolved = n_crit = 0
        for c in self.latest_by_target(project_id).values():
            objs = c.get("objections") or []
            if not objs:
                continue
            n_crit += 1
            total += len(objs)
            sts = c.get("objections_status") or []
            resolved += sum(1 for s in sts if s == "resolved")
        if total == 0:
            return {"score": None, "note": "sin objeciones registradas aún",
                    "resolved": 0, "total": 0}
        return {"score": round(10 * resolved / total, 1), "resolved": resolved,
                "total": total, "critiques": n_crit}

    # --- queries ---------------------------------------------------------------
    def latest_by_target(self, project_id: str) -> dict[str, dict[str, Any]]:
        """Newest critique per target entity (hypothesis/experiment id)."""
        out: dict[str, dict[str, Any]] = {}
        for c in self.store.list_objects(project_id, kind="critique"):
            t = c.get("target_id", "")
            if t and (t not in out
                      or (c.get("created_at") or "") > (out[t].get("created_at") or "")):
                out[t] = c
        return out


def critique_async(project_id: str, target_id: str, task: str, context: str,
                   session_factory: Any | None = None) -> None:
    """Fire-and-forget critique — never blocks or breaks the research flow."""
    import os
    if os.environ.get("ACERO_CRITIC_DISABLED") == "1":       # tests / opt-out
        return

    def _run() -> None:
        try:
            CriticAgent(session_factory).critique_now(
                project_id, target_id, task, context, use_ai=True)
        except Exception:  # noqa: BLE001 - the critic must never break the flow
            pass
    try:
        _POOL.submit(_run)
    except Exception:  # noqa: BLE001
        pass
