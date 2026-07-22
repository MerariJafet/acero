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
    def critique_now(self, project_id: str, target_id: str, task: str,
                     context: str, *, use_ai: bool = True) -> dict[str, Any]:
        out = self._review(project_id, task, context, use_ai=use_ai)
        rec = {"id": new_id("crit"), "target_id": target_id, "task": task,
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
