"""Novelty filter — steer effort toward DISCOVERY, not confirmation.

Discovery never comes from re-testing settled facts. Before we spend experiments
on a hypothesis, this asks (against the project's REAL literature): is this
already answered, actively debated, open, or genuinely unexplored? — and WHY.
It also names what is ALREADY KNOWN and the GAP a fresh experiment could fill.

status ladder (higher = closer to the frontier):
  asentada     — la literatura ya la responde; confirmarla no aporta conocimiento
  en_debate    — controversia activa; aún se puede aportar, pero es terreno pisado
  abierta      — pregunta abierta con datos disponibles y ángulos sin analizar
  inexplorada  — casi nadie la ha atacado; alto potencial de descubrimiento

Honest: this is an LLM aid to PRIORITIZE — it never proves novelty, and a low
score is a warning, not a veto. The human decides what to pursue.
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

_STATUS = ("asentada", "en_debate", "abierta", "inexplorada")
_SCORE = {"asentada": 2.0, "en_debate": 5.0, "abierta": 7.5, "inexplorada": 9.0}

NOVELTY_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},          # asentada|en_debate|abierta|inexplorada
        "known": {"type": "string"},            # qué ya sabe la literatura
        "gap": {"type": "string"},              # el hueco / lo que NO se ha hecho
        "discovery_path": {"type": "string"},   # cómo un experimento podría descubrir algo nuevo
        "reason": {"type": "string"},
    },
    "required": ["status", "known", "gap", "discovery_path", "reason"],
    "additionalProperties": False,
}


class NoveltyFilter:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    def _lit_context(self, project_id: str, limit: int = 6) -> str:
        lit = sorted((p for p in self.store.list_objects(project_id, kind="literature")
                      if p.get("abstract")),
                     key=lambda p: p.get("relevance") or 0, reverse=True)[:limit]
        if not lit:
            return "(sin literatura indexada aún — evalúa por conocimiento del dominio)"
        return "\n".join(f"- «{p.get('title','')}»: {(p.get('abstract') or '')[:280]}"
                         for p in lit)

    def assess(self, project_id: str, hyp_id: str, *, use_ai: bool = True
               ) -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        out = self._assess(project_id, h, use_ai=use_ai)
        self.store.update_payload(hyp_id, {"novelty": out})
        return {"ok": True, **out}

    def _assess(self, project_id: str, h: dict[str, Any], *, use_ai: bool
                ) -> dict[str, Any]:
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=150)
                if prov.available():
                    lit = self._lit_context(project_id)
                    out = prov.complete_json(
                        "Evalúa la NOVEDAD de esta hipótesis para DIRIGIR el esfuerzo "
                        "hacia el descubrimiento, no la confirmación.\n"
                        f"Hipótesis: «{h.get('title','')}». Pregunta detonante: "
                        f"{h.get('trigger_question','')}.\n\n"
                        f"Literatura real del proyecto:\n{lit}\n\n"
                        "Devuelve status (asentada=la literatura ya la responde; "
                        "en_debate=controversia activa; abierta=pregunta abierta con "
                        "datos y ángulos sin analizar; inexplorada=casi nadie la ha "
                        "atacado), known (qué ya se sabe con certeza), gap (qué NO se "
                        "ha hecho/medido/combinado), discovery_path (cómo un "
                        "experimento concreto podría revelar algo NUEVO — cruzar "
                        "catálogos, buscar residuos/anomalías, probar una predicción "
                        "sin verificar), y reason. Sé escéptico: si ya se sabe, dilo "
                        "aunque incomode. En español.",
                        NOVELTY_SCHEMA, temperature=0.3)
                    status = out.get("status", "abierta")
                    if status not in _STATUS:
                        status = "abierta"
                    return {"provider": "codex", "status": status,
                            "score": _SCORE.get(status, 6.0),
                            "known": out.get("known", ""), "gap": out.get("gap", ""),
                            "discovery_path": out.get("discovery_path", ""),
                            "reason": out.get("reason", ""), "assessed_at": now_iso()}
            except Exception:  # noqa: BLE001
                pass
        return {"provider": "none", "status": "sin_evaluar", "score": None,
                "known": "", "gap": "",
                "discovery_path": "Consulta a Aristóteles / evalúa novedad para saber "
                                  "si vale la pena antes de invertir experimentos.",
                "reason": "evaluador IA no disponible", "assessed_at": now_iso()}

    def assess_all(self, project_id: str, *, use_ai: bool = True) -> dict[str, Any]:
        done = []
        for h in self.store.list_objects(project_id, kind="candidate"):
            if h.get("novelty"):
                continue
            r = self.assess(project_id, h["id"], use_ai=use_ai)
            done.append({"tag": h.get("tag"), "status": r.get("status")})
        return {"ok": True, "assessed": done}


def assess_async(project_id: str, hyp_ids: list[str],
                 session_factory: Any | None = None) -> None:
    """Fire-and-forget novelty assessment after hypotheses are generated."""
    import os
    import threading
    if os.environ.get("ACERO_CRITIC_DISABLED") == "1":     # same guard as the critic
        return

    def _run() -> None:
        try:
            nf = NoveltyFilter(session_factory)
            for hid in hyp_ids:
                nf.assess(project_id, hid, use_ai=True)
        except Exception:  # noqa: BLE001
            pass
    threading.Thread(target=_run, name="novelty", daemon=True).start()
