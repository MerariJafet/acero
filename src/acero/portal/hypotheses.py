"""Critical + creative hypothesis generation (Codex CLI local).

The LLM is instructed to QUESTION, not repeat: for a research question it proposes
competing hypotheses across four kinds — established (worth re-checking), theorized
(testable predictions), novel (new relations) and open_question (unanswered) — and
for EACH one records the detonating question, the argument for it, the doubt that
keeps it uncertain, and a concrete computational test. Output is a drafting aid,
NEVER evidence; hypotheses are candidates to test, not claims.
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

HYP_SCHEMA = {
    "type": "object",
    "properties": {
        "hypotheses": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "kind": {"type": "string"},   # established|theorized|novel|open_question
                "discovery_angle": {"type": "string"},  # ver DISCOVERY_ANGLE
                "trigger_question": {"type": "string"},
                "argument": {"type": "string"},
                "doubt": {"type": "string"},
                "test_idea": {"type": "string"},
                "competes_with": {"type": "string"},
            },
            "required": ["title", "kind", "discovery_angle", "trigger_question",
                         "argument", "doubt", "test_idea", "competes_with"],
            "additionalProperties": False}},
    },
    "required": ["hypotheses"],
    "additionalProperties": False,
}

KIND_LABEL = {
    "established": "Ya probado (re-examinar)",
    "theorized": "Ya teorizado (poner a prueba)",
    "novel": "Totalmente nuevo",
    "open_question": "Pregunta abierta",
}

# the four structural sources of NEW knowledge (not confirmation)
DISCOVERY_ANGLE = {
    "cross_data": "Cruce de datos — unir dos catálogos que nadie ha combinado",
    "anomaly": "Anomalía/residuo — lo que NO encaja, sub-poblaciones, outliers",
    "open_untested": "Pregunta abierta con datos disponibles y ángulo sin analizar",
    "untested_prediction": "Predicción sin probar — un modelo dice X, nadie verificó X",
}


class HypothesisService:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    def _grounding(self, project_id: str) -> str:
        lit = self.store.list_objects(project_id, kind="literature")
        angles = sorted({li.get("angle", "") for li in lit if li.get("angle")})
        existing = [h.get("title") or h.get("description", "")
                    for h in self.store.list_objects(project_id, kind="candidate")]
        return (f"Ángulos ya investigados: {', '.join(angles) or 'ninguno'}. "
                f"Hipótesis existentes (NO las repitas, cuestiónalas o ve más allá): "
                f"{'; '.join(x[:60] for x in existing[:8]) or 'ninguna'}.")

    def generate(self, project_id: str, *, n: int = 6, use_ai: bool = True,
                 focus: str = "") -> dict[str, Any]:
        p = self.ledger.get_project(project_id)
        if p is None:
            return {"ok": False, "error": "project not found"}
        # the free-text topic/question the researcher gave at project creation
        topic = focus.strip()
        if not topic:
            briefs = self.store.list_objects(project_id, kind="brief")
            topic = str((briefs[0].get("topic") if briefs else "") or "")
        topic_ctx = (f"\n\nTEMA/PREGUNTA del investigador (guía las hipótesis): "
                     f"«{topic[:400]}».\n") if topic else ""
        hyps: list[dict[str, Any]] | None = None
        provider = "deterministic"
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=220)
                if prov.available():
                    from .playbook import brief
                    prompt = (
                        brief() + "\n\n---\n\n"
                        "Eres un científico ESCÉPTICO y CREATIVO en ACERO. La META es "
                        "DESCUBRIR conocimiento NUEVO, no confirmar lo ya sabido. El "
                        "descubrimiento NUNCA sale de re-testear lo asentado; sale de "
                        "cuatro fuentes — apunta a ellas con discovery_angle:\n"
                        "  cross_data: cruzar DOS catálogos/datasets que nadie ha unido "
                        "(ahí aparecen correlaciones nuevas).\n"
                        "  anomaly: buscar lo que NO encaja — residuos, sub-poblaciones, "
                        "outliers, correlaciones fuera de lo esperado.\n"
                        "  open_untested: una pregunta ABIERTA donde los datos EXISTEN "
                        "pero el análisis concreto no se ha hecho.\n"
                        "  untested_prediction: una predicción específica de un modelo "
                        "que NADIE ha verificado contra datos.\n\n"
                        + topic_ctx +
                        f"Investigación «{p.title}» (dominio {p.domain}). Propón {n} "
                        "hipótesis COMPETIDORAS, verificables con datos PÚBLICOS reales, "
                        "y SESGADAS HACIA LA FRONTERA: evita lo que la literatura ya "
                        "resolvió; prefiere ángulos poco explorados. Para CADA una: "
                        "title, kind (established|theorized|novel|open_question), "
                        "discovery_angle (cross_data|anomaly|open_untested|"
                        "untested_prediction), trigger_question (la duda concreta que "
                        "la origina), argument (por qué es plausible Y por qué sería "
                        "NUEVA si se confirma/refuta), doubt (qué la falsaría), test_idea "
                        "(experimento concreto con datos reales, nombrando los "
                        "catálogos/datasets a CRUZAR o el residuo a buscar, con "
                        "controles/nulos), competes_with. En español. Provocador pero "
                        "riguroso; nada es un descubrimiento hasta probarlo. "
                        + (f"Enfócate en: {focus}." if focus else ""))
                    out = prov.complete_json(prompt, HYP_SCHEMA, temperature=0.6)
                    hyps = out.get("hypotheses") if out else None
                    provider = "codex"
            except Exception:  # noqa: BLE001
                hyps = None
        if not hyps:
            hyps = self._deterministic(p.title, self._grounding(project_id))
            provider = "deterministic"

        created = []
        base = len(self.store.list_objects(project_id, kind="candidate"))
        for i, h in enumerate(hyps):
            hid = new_id("hyp")
            tag = f"H{base + i}"
            payload = {"id": hid, "tag": tag, "title": h.get("title", ""),
                       "description": h.get("title", ""),
                       "kind": h.get("kind", "open_question"),
                       "discovery_angle": h.get("discovery_angle", ""),
                       "trigger_question": h.get("trigger_question", ""),
                       "argument": h.get("argument", ""), "doubt": h.get("doubt", ""),
                       "test_idea": h.get("test_idea", ""),
                       "competes_with": h.get("competes_with", ""),
                       "provider": provider, "generated": True,
                       "created_at": now_iso(), "status": "PROPOSED", "synthetic": False}
            self.store.put(project_id, "candidate", hid, payload, status="PROPOSED",
                           actor="hypothesis_engine",
                           summary=f"hipótesis crítica {tag} ({provider})")
            created.append(payload)
        from .critic import critique_async
        for c in created:
            critique_async(project_id, c["id"], "hipotesis",
                           f"Hipótesis {c['tag']}: {c['title']}\n"
                           f"Pregunta detonante: {c['trigger_question']}\n"
                           f"Argumento: {c['argument']}\nDuda: {c['doubt']}\n"
                           f"Idea de prueba: {c['test_idea']}", self._sf)
        # novelty filter: flag which are frontier vs already-settled (async)
        from .novelty import assess_async
        assess_async(project_id, [c["id"] for c in created], self._sf)
        return {"ok": True, "provider": provider, "created": created,
                "disclaimer": "Hipótesis generadas como candidatos a PROBAR; no son "
                              "evidencia ni descubrimientos."}

    def _deterministic(self, title: str, grounding: str) -> list[dict[str, Any]]:
        return [
            {"title": f"H0 (nula): el patrón en «{title}» es ruido + tendencia",
             "kind": "established", "trigger_question": "¿Y si no hay señal real?",
             "argument": "Toda afirmación debe superar a la explicación más simple.",
             "doubt": "Podría descartarse con SNR alto y nulos controlados.",
             "test_idea": "Comparar contra surrogatos de ruido rojo y datos barajados.",
             "competes_with": "cualquier hipótesis de señal"},
            {"title": "Un mecanismo conocido reproduce la observación",
             "kind": "theorized", "trigger_question": "¿La teoría estándar ya lo predice?",
             "argument": "Si un modelo establecido ajusta, no se necesita física nueva.",
             "doubt": "El ajuste podría ser degenerado con otros modelos.",
             "test_idea": "Ajustar el modelo estándar y medir residuales.",
             "competes_with": "hipótesis novedosa"},
            {"title": "Una relación no reportada conecta dos variables del sistema",
             "kind": "novel", "trigger_question": "¿Qué correlación NADIE ha mirado aquí?",
             "argument": "Los datos públicos permiten cruces poco explorados.",
             "doubt": "Correlación no implica causalidad; riesgo de multiple testing.",
             "test_idea": "Buscar la relación y controlar con FDR + validación cruzada.",
             "competes_with": "mecanismo conocido"},
        ]

    def get(self, hyp_id: str) -> dict[str, Any] | None:
        return self.store.get(hyp_id)
