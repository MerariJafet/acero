"""RAMANUJAN — la chispa creativa en la frontera.

Cuando el flujo llega a "no se puede con las herramientas actuales", este motor NO
acepta el no: genera ideas de ataque laterales al estilo "¿y si mejor usamos
matrices?" — analogías entre ramas, reformulaciones, puentes inesperados entre las
piezas del TOOLBOX. Cada idea trae posibilidad/probabilidad HONESTAS y el primer
experimento concreto que la pondría a prueba.

Honestidad: una chispa es una HIPÓTESIS de método, jamás un resultado. La probabilidad
es una apuesta declarada del modelo, no una medición. Todo lo que salga de aquí debe
pasar por Turing (experimento real) y por el resto del Consejo.
"""
from __future__ import annotations

from typing import Any

from . import toolbox

SPARK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chispa": {"type": "string",
                               "description": "la idea en una frase '¿y si...?'"},
                    "analogia": {"type": "string",
                                 "description": "de dónde viene la intuición (qué rama/truco se parece)"},
                    "plan": {"type": "string",
                             "description": "cómo se combinan las piezas, paso a paso"},
                    "piezas": {"type": "array", "items": {"type": "string"},
                               "description": "herramientas del catálogo que usa"},
                    "piezas_faltantes": {"type": "array", "items": {"type": "string"},
                                         "description": "lo que habría que instalar o CREAR en python"},
                    "probabilidad": {"type": "number",
                                     "description": "apuesta honesta 0-1 de que aporte algo"},
                    "primer_experimento": {"type": "string",
                                           "description": "el experimento MÁS BARATO que la mata o la aviva"},
                },
                "required": ["chispa", "analogia", "plan", "piezas",
                             "piezas_faltantes", "probabilidad", "primer_experimento"],
                "additionalProperties": False,     # Codex exige esquemas estrictos
            },
        },
    },
    "required": ["ideas"],
    "additionalProperties": False,
}

_SPARK_SYS = """Eres Ramanujan en el Consejo de ACERO: intuición matemática salvaje con
los pies en la tierra. Te presentan una FRONTERA: algo donde los métodos actuales se
agotaron y "los problemas dicen no se puede". Tu trabajo es responder: ¿y si sí?

Reglas de la chispa:
- Genera ideas LATERALES, no más-de-lo-mismo: cambia de representación (¿matrices?
  ¿generatrices? ¿geometría? ¿probabilidad?), importa trucos de otra rama, reformula
  el objeto, invierte el problema, busca el caso especial revelador.
- Cada idea DEBE decir qué piezas del catálogo usa y qué le falta (que se pueda
  instalar o programar en Python — tenemos el poder de programar).
- Sé honesto con la probabilidad: 0.05 es una apuesta digna si la idea es hermosa;
  no infles. Una chispa es una hipótesis de método, no un resultado.
- El primer_experimento debe ser BARATO y decisivo: lo que la mata o la aviva en
  minutos u horas, no en meses."""


class SparkEngine:
    """Genera chispas de ataque para una frontera, ancladas al TOOLBOX real."""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def ignite(self, frontier: str, why_stuck: str, n_ideas: int = 5,
               extra_context: str = "") -> list[dict[str, Any]]:
        """frontier: qué queremos romper. why_stuck: por qué lo actual no alcanza.
        Devuelve ideas ordenadas por probabilidad (apuesta declarada, no medición)."""
        cat = toolbox.catalog_text()
        prompt = (
            f"{_SPARK_SYS}\n\nFRONTERA:\n{frontier}\n\n"
            f"POR QUÉ ESTAMOS ATORADOS:\n{why_stuck}\n\n"
            f"CATÁLOGO DE PIEZAS (LEGO):\n{cat}\n"
            + (f"\nCONTEXTO EXTRA:\n{extra_context}\n" if extra_context else "")
            + f"\nGenera {n_ideas} chispas distintas entre sí."
        )
        out = self._provider.complete_json(prompt, SPARK_SCHEMA, temperature=0.9)
        ideas = list(out.get("ideas") or [])
        for i in ideas:  # saneo defensivo de la apuesta
            p = i.get("probabilidad")
            i["probabilidad"] = min(max(float(p), 0.0), 1.0) if isinstance(
                p, (int, float)) else 0.0
        return sorted(ideas, key=lambda i: -i["probabilidad"])[:n_ideas]
