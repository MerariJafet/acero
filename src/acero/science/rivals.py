"""Teorías RIVALES y experimentos DISCRIMINANTES — el par que hace ciencia.

Dos capacidades que existían desconectadas del ciclo (`epistemic/
rival_theory_generator.py` y `inference/active_experiments/discriminating.py`)
y aquí quedan alcanzables como jugadas de Bohr, sin duplicar sus motores:
el cálculo de ganancia de información reutiliza `discovery/information_gain.py`.

Por qué importa: un patrón sin rivales explícitas es una historia bonita. La
pregunta que convierte observación en ciencia no es "¿esto encaja?" sino "¿qué
OTRA cosa produciría exactamente lo mismo, y qué experimento las separa?".

Adaptado al dominio: en matemáticas las rivales NO son causales (no hay "X causa
Y"); son explicaciones alternativas del mismo hecho — artefacto del muestreo,
consecuencia de una definición, caso degenerado, teorema conocido disfrazado.
Forzar causalidad donde no aplica sería un error de categoría.
"""

from __future__ import annotations

from typing import Any

RIVALS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rivales": {
            "type": "array", "minItems": 2, "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "teoria": {"type": "string",
                               "description": "explicación alternativa concreta"},
                    "tipo": {"type": "string",
                             "description": "mecanismo_directo | relacion_inversa | "
                                            "causa_comun | artefacto_seleccion | "
                                            "artefacto_medicion | consecuencia_de_"
                                            "definicion | caso_degenerado | "
                                            "resultado_conocido | nulo_azar"},
                    "prediccion_distintiva": {
                        "type": "string",
                        "description": "qué predeciría ESTA teoría y NO las otras "
                                       "— lo que la hace distinguible"},
                    "como_matarla": {"type": "string",
                                     "description": "el experimento/cálculo que la "
                                                    "refutaría"},
                },
                "required": ["teoria", "tipo", "prediccion_distintiva",
                             "como_matarla"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["rivales"],
    "additionalProperties": False,
}

_RIVALS_SYS = """Eres el generador de teorías RIVALES de ACERO. Te dan un patrón o
conjetura y produces 2-5 explicaciones ALTERNATIVAS genuinas del MISMO hecho.

Reglas:
- En MATEMÁTICAS no fuerces causalidad: las rivales son 'esto también produciría
  lo observado' — consecuencia trivial de una definición, artefacto del rango
  muestreado, caso degenerado, teorema clásico disfrazado, coincidencia numérica.
- En dominios empíricos sí valen mecanismo directo/inverso/causa común/sesgo de
  selección/artefacto de medición.
- Cada rival DEBE traer una predicción DISTINTIVA (algo que ella predice y las
  demás no) y cómo matarla. Una rival que no se puede distinguir no sirve.
- Incluye SIEMPRE la explicación nula (azar/artefacto) como una de las rivales.
- Rivales de paja están prohibidas: deben ser plausibles de verdad."""

DISCRIMINATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "experimento": {"type": "string",
                        "description": "el experimento concreto que más separa"},
        "predicciones": {
            "type": "array",
            "description": "qué resultado espera CADA rival (mismo orden que se "
                           "te dieron); si dos coinciden, dilo",
            "items": {"type": "object",
                      "properties": {
                          "teoria": {"type": "string"},
                          "resultado_esperado": {"type": "string"},
                      },
                      "required": ["teoria", "resultado_esperado"],
                      "additionalProperties": False}},
        "resultados_distinguibles": {
            "type": "number",
            "description": "cuántos resultados DISTINTOS entre sí producen las "
                           "rivales (2 = separa en dos grupos, n = separa todas)"},
        "criterio": {"type": "string",
                     "description": "qué observación mataría a cuál"},
    },
    "required": ["experimento", "predicciones", "resultados_distinguibles",
                 "criterio"],
    "additionalProperties": False,
}

_DISC_SYS = """Diseña el experimento que MAXIMICE el desacuerdo entre las teorías
rivales dadas. No el experimento más bonito ni el más barato: el que produce
resultados MÁS DISTINTOS según cuál rival sea cierta.

Un experimento donde todas predicen ~lo mismo NO sirve, aunque suene impresionante.
Prefiere el que parte el conjunto de rivales por la mitad. Sé concreto y ejecutable."""


def generate_rivals(provider: Any, claim: str, *, domain: str | None = None
                    ) -> list[dict[str, Any]]:
    """Rivales explícitas para un patrón/conjetura. Nunca lanza: sin proveedor
    devuelve [] y el ciclo sigue (una capacidad caída no mata la investigación)."""
    prompt = (f"{_RIVALS_SYS}\n\nDOMINIO: {domain or 'matemáticas'}\n"
              f"PATRÓN/CONJETURA:\n{claim}")
    try:
        out = provider.complete_json(prompt, RIVALS_SCHEMA, temperature=0.6)
    except Exception:  # noqa: BLE001
        return []
    return [r for r in (out.get("rivales") or []) if isinstance(r, dict)]


def design_discriminating(provider: Any, claim: str,
                          rivals: list[dict[str, Any]]) -> dict[str, Any]:
    """Experimento discriminante + su ganancia de información CALCULADA.

    El LLM propone el diseño y las predicciones; el EIG lo calcula el motor real
    (`discovery/information_gain.py`) a partir de cuántos resultados distintos
    genera — el LLM no puede inflar ese número a su favor porque entra como
    conteo, no como puntaje."""
    if len(rivals) < 2:
        return {"experimento": "", "eig": None,
                "why": "se necesitan ≥2 rivales para discriminar"}
    listado = "\n".join(f"- [{r.get('tipo')}] {r.get('teoria')} "
                        f"(predice: {r.get('prediccion_distintiva')})"
                        for r in rivals)
    prompt = f"{_DISC_SYS}\n\nAFIRMACIÓN:\n{claim}\n\nRIVALES VIVAS:\n{listado}"
    try:
        out = provider.complete_json(prompt, DISCRIMINATE_SCHEMA, temperature=0.3)
    except Exception as exc:  # noqa: BLE001
        return {"experimento": "", "eig": None, "why": str(exc)[:120]}
    from ..discovery.information_gain import heuristic_eig
    import math
    n_out = max(1, int(out.get("resultados_distinguibles") or 1))
    res = heuristic_eig(len(rivals), n_out)
    denom = math.log2(len(rivals)) or 1.0
    return {**out, "eig": round(min(1.0, res.eig / denom), 4),
            "eig_bits": round(res.eig, 4), "n_rivales": len(rivals),
            "estimator": "heuristic_eig (cota superior declarada)"}
