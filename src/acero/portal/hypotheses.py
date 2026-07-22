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
                "trigger_question": {"type": "string"},
                "argument": {"type": "string"},
                "doubt": {"type": "string"},
                "test_idea": {"type": "string"},
                "competes_with": {"type": "string"},
            },
            "required": ["title", "kind", "trigger_question", "argument", "doubt",
                         "test_idea", "competes_with"],
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
        hyps: list[dict[str, Any]] | None = None
        provider = "deterministic"
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=220)
                if prov.available():
                    prompt = (
                        "Eres un científico ESCÉPTICO y CREATIVO en ACERO. Para la "
                        f"investigación «{p.title}» (dominio {p.domain}) propón {n} hipótesis "
                        "COMPETIDORAS y verificables computacionalmente. NO repitas "
                        "conocimiento de libro: CUESTIÓNALO. Cubre las cuatro clases: "
                        "'established' (algo dado por cierto que vale re-examinar), "
                        "'theorized' (una teoría con predicción falsable), 'novel' (una "
                        "relación o idea genuinamente nueva/atrevida) y 'open_question' "
                        "(algo aún sin respuesta). Para CADA hipótesis da: title (la "
                        "hipótesis), kind, trigger_question (la PREGUNTA DETONANTE que la "
                        "origina — la duda concreta), argument (por qué es plausible), "
                        "doubt (qué la haría falsa o qué la vuelve incierta), test_idea "
                        "(cómo probarla con datos PÚBLICOS reales y controles/nulos), "
                        "competes_with (a qué hipótesis se opone). En español. Sé "
                        "provocador pero riguroso; nada es un descubrimiento. "
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
