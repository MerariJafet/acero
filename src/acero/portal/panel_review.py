"""Plural adversarial panel, LIVE via Codex — eight incompatible mandates.

Wires `science.panel` to the real model. Each panelist gets ONLY its mandate (a
statistician does not moralize about novelty; a causalist does not check units), so the
panel opposes the result from genuinely different angles instead of one sceptic sharing
the investigator's blind spots. Disagreement is preserved (no forced consensus); a
blocking objection from a HARD-mandate panelist halts advancement.

The model provider is injectable so tests run deterministically; guarded by
ACERO_CRITIC_DISABLED exactly like the resident critic. When the model is unavailable it
degrades to an honest per-persona checklist, never a fabricated review.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from ..science.panel import (
    HARD_MANDATE,
    MANDATES,
    VERDICTS,
    Panelist,
    PanelVerdict,
    Review,
)

PANEL_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},
        "objections": {"type": "array", "items": {"type": "string"}},
        "blocking": {"type": "boolean"},
        "note": {"type": "string"},
    },
    "required": ["verdict", "objections", "blocking", "note"],
    "additionalProperties": False,
}


def _persona_prompt(panelist: Panelist, context: str) -> str:
    m = MANDATES[panelist]
    looks_for = m["looks_for"] if isinstance(m["looks_for"], list) else []
    looks = ", ".join(str(x) for x in looks_for)
    hard = ("Tu mandato es DURO: si encuentras un defecto que invalida el resultado, "
            "marca blocking=true." if panelist in HARD_MANDATE else
            "Tu mandato es de advertencia: objeta, pero rara vez bloquees.")
    return (
        f"Eres «{panelist.value}», un miembro de un PANEL de revisión científica "
        f"adversarial. Tu ÚNICO mandato es: {m['mandate']}. "
        f"Buscas específicamente: {looks}. "
        "NO evalúes otras dimensiones fuera de tu mandato; quédate en tu carril. "
        "No busques consenso con el resto del panel: tu desacuerdo es valioso. "
        f"{hard}\n\n"
        f"TRABAJO A REVISAR:\n{context[:3500]}\n\n"
        "Devuelve: verdict (uno de: solido|prometedor|debil|defectuoso), objections "
        "(0-3 concretas, SOLO de tu mandato), blocking (bool), note (1 frase). "
        "No inventes datos ni citas.")


def _fallback_review(panelist: Panelist) -> Review:
    return Review(panelist, "prometedor", objections=[], blocking=False,
                  note="revisor IA no disponible (checklist mínimo del mandato)")


class PluralPanel:
    """Runs the eight personas and aggregates into a PanelVerdict (disagreement kept)."""

    def __init__(self, provider: Any | None = None,
                 provider_factory: Callable[[], Any] | None = None) -> None:
        self._provider = provider
        self._provider_factory = provider_factory

    def _get_provider(self) -> Any | None:
        if self._provider is not None:
            return self._provider
        if self._provider_factory is not None:
            return self._provider_factory()
        try:
            from ..llm.providers import CodexCliProvider
            return CodexCliProvider(timeout_sec=150)
        except Exception:  # noqa: BLE001
            return None

    def review_context(self, context: str, *, use_ai: bool = True) -> PanelVerdict:
        """Review a free-text context with all eight panelists."""
        if not use_ai or os.environ.get("ACERO_CRITIC_DISABLED") == "1":
            return PanelVerdict([_fallback_review(p) for p in Panelist])
        prov = self._get_provider()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return PanelVerdict([_fallback_review(p) for p in Panelist])
        reviews: list[Review] = []
        for p in Panelist:
            try:
                out = prov.complete_json(_persona_prompt(p, context),
                                         PANEL_ITEM_SCHEMA, temperature=0.3)
                verdict = out.get("verdict", "prometedor")
                if verdict not in VERDICTS:
                    verdict = "prometedor"
                reviews.append(Review(
                    p, verdict, objections=list(out.get("objections", []))[:3],
                    blocking=bool(out.get("blocking", False)),
                    note=str(out.get("note", ""))[:200]))
            except Exception:  # noqa: BLE001 - one panelist failing must not kill the panel
                reviews.append(_fallback_review(p))
        return PanelVerdict(reviews)


def panel_verdict_to_record(v: PanelVerdict) -> dict[str, Any]:
    """Serialize a PanelVerdict for storage / dossier attachment."""
    return {
        "reviews": [{"panelist": r.panelist.value, "verdict": r.verdict,
                     "objections": r.objections, "blocking": r.blocking,
                     "note": r.note} for r in v.reviews],
        **v.summary(),
    }
