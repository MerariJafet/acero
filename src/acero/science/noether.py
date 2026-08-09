"""NOETHER — la teórica de números del Consejo: árbitra estilo referee de journal.

Emmy Noether revisa resultados matemáticos como lo haría la revisora más dura de
un journal de teoría de números: verifica los enunciados de los teoremas contra
sus pruebas, distingue sin piedad TEOREMA / EVIDENCIA / CONJETURA, ataca la
novedad contra la literatura que conoce, exige los chequeos que faltan y emite
un dictamen accionable (aceptar / revisión menor / revisión mayor / rechazar).

LÍNEA ROJA CONSTITUCIONAL: Noether es parte del sistema autor. Su arbitraje
ELEVA el rigor interno pero NUNCA cuenta como validación externa — la
attestation final es de un experto HUMANO ajeno al sistema. Todo informe suyo
termina recordándolo.
"""
from __future__ import annotations

from typing import Any

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "veredicto": {"type": "string",
                      "description": "aceptar | revision_menor | revision_mayor | rechazar"},
        "resumen": {"type": "string",
                    "description": "qué afirma el trabajo y qué tan sólido es, en 3-5 frases"},
        "fortalezas": {"type": "array", "items": {"type": "string"}},
        "objeciones_mayores": {"type": "array", "items": {"type": "string"},
                               "description": "lo que BLOQUEA publicación; específicas y accionables"},
        "objeciones_menores": {"type": "array", "items": {"type": "string"}},
        "literatura_faltante": {"type": "array", "items": {"type": "string"},
                                "description": "trabajos/temas que el manuscrito debe citar o descartar"},
        "chequeos_sugeridos": {"type": "array", "items": {"type": "string"},
                               "description": "verificaciones computacionales/simbólicas concretas"},
        "dictamen_novedad": {"type": "string",
                             "description": "qué partes son nuevas, cuáles folclor, y el riesgo de solapamiento"},
    },
    "required": ["veredicto", "resumen", "fortalezas", "objeciones_mayores",
                 "objeciones_menores", "literatura_faltante", "chequeos_sugeridos",
                 "dictamen_novedad"],
    "additionalProperties": False,
}

_NOETHER_SYS = """Eres Emmy Noether arbitrando para un journal serio de teoría de
números. Recibes un manuscrito (nota corta) con teoremas, evidencia computacional y
conjeturas sobre la conjetura de Erdős–Straus en sus clases duras mod 840.

Tu método de referee:
1. AFIRMACIONES EXACTAS: reconstruye cada claim y clasifícalo sin piedad:
   TEOREMA (¿la prueba dada realmente prueba lo enunciado? revisa el álgebra),
   EVIDENCIA (¿el cómputo soporta exactamente lo que se dice, ni más?),
   CONJETURA (¿está bien formulada y es falsable?).
2. NOVEDAD: compara contra lo que conoces — verificaciones computacionales
   (Swett, Salez 10^17), identidades de Mordell, obstrucción de Schinzel,
   densidades (Vaughan, Webb), conteo de soluciones (Elsholtz–Tao), y los
   trabajos por congruencias citados en el propio manuscrito. Señala solapes.
3. HUECOS: qué chequeo mataría o consolidaría cada claim débil; qué falta citar.
4. Sé DURA pero constructiva: cada objeción debe decir cómo resolverse.
5. No inventes citas: si no recuerdas la referencia exacta, describe el tema a
   buscar. Distingue 'no lo conozco' de 'no existe'."""


class NoetherReviewer:
    """Arbitraje experto (simulado) — inyectable para tests."""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def referee(self, manuscript: str, extra_evidence: str = "") -> dict[str, Any]:
        prompt = (f"{_NOETHER_SYS}\n\nMANUSCRITO:\n{manuscript[:14000]}\n"
                  + (f"\nEVIDENCIA ADICIONAL (registros de cómputo):\n"
                     f"{extra_evidence[:3000]}\n" if extra_evidence else "")
                  + "\nEmite tu informe de referee.")
        out = self._provider.complete_json(prompt, REVIEW_SCHEMA, temperature=0.3)
        out["nota_constitucional"] = (
            "Este arbitraje es INTERNO (sistema autor). No sustituye la "
            "validación externa humana requerida por la constitución de ACERO.")
        return out


def render_report(r: dict[str, Any]) -> str:
    """Informe de referee en markdown, listo para el repo."""
    def _sec(title: str, items: list[str]) -> str:
        if not items:
            return f"## {title}\n\n(ninguna)\n"
        return f"## {title}\n\n" + "\n".join(f"- {i}" for i in items) + "\n"
    return (f"# Informe de referee — Noether (arbitraje interno)\n\n"
            f"**Veredicto:** {r.get('veredicto')}\n\n"
            f"**Resumen del árbitro:** {r.get('resumen')}\n\n"
            + _sec("Fortalezas", r.get("fortalezas") or [])
            + _sec("Objeciones MAYORES (bloquean)", r.get("objeciones_mayores") or [])
            + _sec("Objeciones menores", r.get("objeciones_menores") or [])
            + _sec("Literatura faltante / a descartar", r.get("literatura_faltante") or [])
            + _sec("Chequeos sugeridos", r.get("chequeos_sugeridos") or [])
            + f"## Dictamen de novedad\n\n{r.get('dictamen_novedad')}\n\n"
            + f"---\n\n*{r.get('nota_constitucional')}*\n")
