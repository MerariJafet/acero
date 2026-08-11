"""POLICY ENGINE — el estratega deja de ser un LLM con poder absoluto.

Crítica del revisor externo (2026-08-10), aceptada: "Bohr no garantiza estrategia
óptima; sus salvaguardas son mecánicas pero su criterio no". La respuesta NO es
quitar a Bohr — es quitarle el poder absoluto:

    Bohr (LLM)  →  propone 2-4 jugadas CANDIDATAS con sus estimaciones
    PolicyEngine (máquina) →  las puntúa y ELIGE, con señales que el LLM
                              no controla, y registra el desglose completo

    Utilidad(a) = wI·I + wF·F + wN·N + wR·R − costo − wK·riesgo − repetición

donde I=información esperada, F=capacidad de falsificación, N=novedad,
R=reducción de incertidumbre (estimaciones del LLM, ACOTADAS a [0,1]) y las
señales MECÁNICAS son:
  * costo: tabla por acción (proporción del presupuesto que suele consumir),
  * riesgo: tabla por acción (epistémico/operativo) + la estimación del LLM,
  * repetición: penalización dura por insistir en una jugada que acaba de dar
    el mismo resultado (rendimientos decrecientes medidos en el HISTORIAL, no
    declarados), y por jugadas que acaban de fallar.

El sistema deja de preguntar "¿qué le parece interesante a un modelo?" y empieza
a preguntar "¿qué jugada maximiza cuánto aprendemos por unidad de cómputo?".
Todo el desglose queda en la decisión del ledger — auditable, no vibes.
"""

from __future__ import annotations

from typing import Any

# Costo relativo típico por acción (fracción cualitativa del presupuesto de una
# ronda). Calibración inicial por experiencia operativa; el Research Genome
# (roadmap) los reemplazará por costos APRENDIDOS del propio ledger.
ACTION_COST: dict[str, float] = {
    "hipatia": 0.05, "kepler": 0.05, "aristoteles": 0.08, "feynman": 0.08,
    "mendeleev": 0.10, "noether": 0.10, "gauss": 0.05, "popper": 0.25,
    "godel": 0.35, "ramanujan": 0.10, "turing": 0.45, "reiniciar": 0.05,
    "cerrar": 0.0,
}

# Riesgo epistémico/operativo base por acción (0-1). 'reiniciar' es LA jugada
# donde históricamente se coló la deriva de premisa; 'cerrar' arriesga dejar
# hilos vivos sin atacar; 'gauss' arriesga empaquetar de más.
ACTION_RISK: dict[str, float] = {
    "reiniciar": 0.45, "cerrar": 0.30, "gauss": 0.25, "turing": 0.15,
    "godel": 0.10, "popper": 0.05, "hipatia": 0.02, "feynman": 0.10,
    "aristoteles": 0.02, "kepler": 0.05, "mendeleev": 0.05, "ramanujan": 0.10,
    "noether": 0.05,
}

WEIGHTS = {"info": 1.5, "falsif": 1.0, "novedad": 0.8, "incert": 0.7,
           "costo": 1.0, "riesgo": 1.2}


def _clip(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def _repetition_penalty(action: str, history: list[dict[str, Any]]) -> float:
    """Rendimientos decrecientes MEDIDOS: repetir una jugada que acaba de dar el
    mismo resumen es casi seguro información nula; una que acaba de fallar,
    peor. Mirar las últimas 6 jugadas (el anti-bucle duro sigue existiendo aparte)."""
    recent = [h for h in history[-6:] if h.get("action") == action]
    if not recent:
        return 0.0
    pen = 0.25 * len(recent)                       # insistencia cuesta
    summaries = [str(h.get("summary"))[:80] for h in recent]
    if len(recent) >= 2 and len(set(summaries)) == 1:
        pen += 0.6                                 # mismo resultado literal: casi nulo
    if any(h.get("error") or "falló" in str(h.get("summary", ""))
           for h in recent[-1:]):
        pen += 0.3                                 # acaba de fallar
    return pen


def score(candidate: dict[str, Any], history: list[dict[str, Any]]
          ) -> dict[str, Any]:
    """Puntúa UNA candidata. Devuelve el desglose completo (auditable)."""
    action = str(candidate.get("action") or "")
    info = _clip(candidate.get("info_esperada"))
    falsif = _clip(candidate.get("falsabilidad"))
    novedad = _clip(candidate.get("novedad"))
    incert = _clip(candidate.get("reduccion_incertidumbre"))
    riesgo_llm = _clip(candidate.get("riesgo"))
    costo = ACTION_COST.get(action, 0.20)
    riesgo = max(ACTION_RISK.get(action, 0.10), riesgo_llm)
    rep = _repetition_penalty(action, history)
    utility = (WEIGHTS["info"] * info + WEIGHTS["falsif"] * falsif
               + WEIGHTS["novedad"] * novedad + WEIGHTS["incert"] * incert
               - WEIGHTS["costo"] * costo - WEIGHTS["riesgo"] * riesgo - rep)
    return {"action": action, "utility": round(utility, 4),
            "desglose": {"info": info, "falsif": falsif, "novedad": novedad,
                         "incert": incert, "costo": costo, "riesgo": riesgo,
                         "repeticion": round(rep, 3)}}


class PolicyEngine:
    """Elige entre las candidatas de Bohr. Determinista y auditable."""

    def choose(self, candidates: list[dict[str, Any]],
               history: list[dict[str, Any]]
               ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """→ (candidata ganadora | None si no hay válidas, scores de todas)."""
        valid = [c for c in candidates
                 if isinstance(c, dict) and str(c.get("action") or "").strip()]
        if not valid:
            return None, []
        scored = [score(c, history) for c in valid]
        best_i = max(range(len(scored)), key=lambda i: scored[i]["utility"])
        winner = dict(valid[best_i])
        winner["_policy"] = {"elegida": scored[best_i],
                             "todas": scored,
                             "regla": "argmax utilidad (pesos fijos v1; costos "
                                      "por tabla; repetición medida en historial)"}
        return winner, scored


PROPOSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidatas": {
            "type": "array", "minItems": 2, "maxItems": 4,
            "description": "2-4 jugadas ALTERNATIVAS reales (no rellenos): "
                           "estrategias distintas que compiten",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string",
                               "description": "una jugada del menú"},
                    "reason": {"type": "string",
                               "description": "por qué esta jugada ahora"},
                    "expected": {"type": "string",
                                 "description": "qué esperas aprender"},
                    "statement": {"type": "string",
                                  "description": "enunciado nuevo si "
                                                 "action=reiniciar ('' si no)"},
                    "frontier": {"type": "string",
                                 "description": "solo ramanujan ('' si no)"},
                    "why_stuck": {"type": "string",
                                  "description": "solo ramanujan ('' si no)"},
                    "idea": {"type": "string",
                             "description": "solo turing ('' si no)"},
                    "piezas": {"type": "array", "items": {"type": "string"},
                               "description": "solo turing ([] si no)"},
                    "budget_min": {"type": "number",
                                   "description": "solo turing (0 = 60)"},
                    "disposition": {"type": "string",
                                    "description": "solo cerrar ('' si no)"},
                    "dataset_ref": {"type": "string",
                                    "description": "solo mendeleev ('' si no)"},
                    "target": {"type": "string",
                               "description": "solo mendeleev ('' si no)"},
                    "info_esperada": {
                        "type": "number",
                        "description": "0-1: cuánta información NUEVA esperas"},
                    "falsabilidad": {
                        "type": "number",
                        "description": "0-1: qué tan capaz es de REFUTAR algo"},
                    "novedad": {
                        "type": "number",
                        "description": "0-1: qué tan distinto de lo ya intentado"},
                    "reduccion_incertidumbre": {
                        "type": "number",
                        "description": "0-1: cuánto acota lo que no sabemos"},
                    "riesgo": {
                        "type": "number",
                        "description": "0-1: riesgo epistémico/operativo"},
                },
                "required": ["action", "reason", "expected", "statement",
                             "frontier", "why_stuck", "idea", "piezas",
                             "budget_min", "disposition", "dataset_ref",
                             "target", "info_esperada", "falsabilidad",
                             "novedad", "reduccion_incertidumbre", "riesgo"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["candidatas"],
    "additionalProperties": False,     # Codex exige esquemas estrictos
}
