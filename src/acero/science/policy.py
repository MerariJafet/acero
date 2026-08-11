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

import math
from typing import Any

# Costo relativo típico por acción (fracción cualitativa del presupuesto de una
# ronda). Calibración inicial por experiencia operativa; el Research Genome
# (roadmap) los reemplazará por costos APRENDIDOS del propio ledger.
ACTION_COST: dict[str, float] = {
    "hipatia": 0.05, "kepler": 0.05, "aristoteles": 0.08, "feynman": 0.08,
    "mendeleev": 0.10, "noether": 0.10, "gauss": 0.05, "popper": 0.25,
    "godel": 0.35, "ramanujan": 0.10, "turing": 0.45, "reiniciar": 0.05,
    "cerrar": 0.0,
    # jugadas LEGO: pensar otra representación o generar rivales es BARATO;
    # diseñar el experimento discriminante cuesta como un experimento medio
    "reinterpretar": 0.06, "rivales": 0.06, "discriminar": 0.22,
}

# Riesgo epistémico/operativo base por acción (0-1). 'reiniciar' es LA jugada
# donde históricamente se coló la deriva de premisa; 'cerrar' arriesga dejar
# hilos vivos sin atacar; 'gauss' arriesga empaquetar de más.
ACTION_RISK: dict[str, float] = {
    "reiniciar": 0.45, "cerrar": 0.30, "gauss": 0.25, "turing": 0.15,
    "godel": 0.10, "popper": 0.05, "hipatia": 0.02, "feynman": 0.10,
    "aristoteles": 0.02, "kepler": 0.05, "mendeleev": 0.05, "ramanujan": 0.10,
    "noether": 0.05,
    # reinterpretar arriesga perder información en la transformación (por eso se
    # exige declararla); rivales de paja y discriminación mal diseñada son leves
    "reinterpretar": 0.18, "rivales": 0.05, "discriminar": 0.08,
}

WEIGHTS = {"info": 1.5, "falsif": 1.0, "novedad": 0.8, "incert": 0.7,
           "costo": 1.0, "riesgo": 1.2}

# Versionado (auditoría externa): los pesos NO son dogma — cada decisión registra
# con qué versión de política se puntuó, para poder recalibrar contra resultados
# reales (Research Genome) sin reescribir la historia.
POLICY_VERSION = "policy-v1"

# NORMALIZACIÓN (contrato explícito): TODAS las variables viven en [0,1].
#   info/falsif/novedad/incert/riesgo_llm → _clip a [0,1] (estimaciones del LLM)
#   costo  → tabla en [0, 0.45] ⊂ [0,1]
#   riesgo → max(tabla, estimación LLM) ∈ [0,1]
#   repetición → [0, ~1.9] (penalización, puede dominar A PROPÓSITO: repetir lo
#   idéntico debe perder contra casi cualquier alternativa)
# Rango resultante de U: aprox [-3.1, +4.0]. Comparable entre candidatas SIEMPRE.

# FUENTES (auditoría externa: "¿quién calcula cada score?"). v1, honesto:
#   proposer (LLM): info, falsif, novedad, incert, riesgo(parcial)
#   mechanical:     costo (tabla), riesgo (piso de tabla), repetición (historial)
#   mechanical:     información (EIG real vía discovery/information_gain),
#                   falsabilidad (tabla estructural), costo, piso de riesgo, repetición
#   historical:     prior v0 minado del propio historial (tasa de utilidad por
#                   acción, con mínimo de muestra; UNKNOWN si no alcanza)
SCORE_SOURCES = {"info": "proposer+mechanical+historical",
                 "falsif": "proposer+mechanical", "novedad": "proposer",
                 "incert": "proposer", "costo": "mechanical",
                 "riesgo": "mechanical+proposer", "repeticion": "mechanical"}


# Acciones con capacidad ESTRUCTURAL de falsificar (no es opinión del LLM: es una
# propiedad del mecanismo). Buscar contraejemplos, probar mecánicamente, diseñar
# un experimento discriminante o predecir sobre holdout PUEDEN devolver un
# resultado que mate una hipótesis. Una revisión narrativa, no.
MECHANICAL_FALSIFIABILITY = {
    "popper": 0.95,        # su producto ES el contraejemplo
    "godel": 0.85,         # unsat/sat decide
    "discriminar": 0.90,   # separa rivales por diseño
    "turing": 0.55,        # depende del experimento que construya
    "mendeleev": 0.25,     # describe estructura; no refuta por sí solo
    "aristoteles": 0.30,   # objeta, no refuta mecánicamente
    "noether": 0.20, "hipatia": 0.35,   # novedad puede matar el aporte
    "kepler": 0.10, "ramanujan": 0.05, "feynman": 0.10,
    "reinterpretar": 0.05, "rivales": 0.15, "gauss": 0.0, "reiniciar": 0.0,
    "cerrar": 0.0,
}


def mechanical_information(candidate: dict[str, Any],
                           state: dict[str, Any] | None = None
                           ) -> tuple[float | None, dict[str, Any]]:
    """Información esperada CALCULADA (no declarada), reutilizando el motor real
    `discovery/information_gain.py` que existía desconectado.

    Si hay rivales cuantificables → EIG bayesiana sobre sus predicciones.
    Si solo se conoce el número de hipótesis y de resultados distintos posibles →
    cota superior heurística log2(k) (el propio módulo la declara como cota, no
    como estimación calibrada).
    Si no hay con qué calcular → **UNKNOWN (None), jamás 0.0**: ausencia de
    cálculo no es ausencia de información — convertirla en 0 castigaría
    exactamente a las ideas nuevas."""
    from ..discovery.information_gain import bayesian_eig, heuristic_eig
    st = state or {}
    rivals = st.get("rivals") or []
    try:
        # caso fuerte: rivales con verosimilitudes por resultado
        likelihoods = {r["id"]: r["likelihoods"] for r in rivals
                       if isinstance(r, dict) and r.get("likelihoods")}
        if len(likelihoods) >= 2:
            prior = {h: 1.0 / len(likelihoods) for h in likelihoods}
            res = bayesian_eig(prior, likelihoods)
            n_max = math.log2(len(likelihoods)) or 1.0
            return min(1.0, res.eig / n_max), {"estimator": "bayesian_eig",
                                               **res.as_dict()}
        # caso débil pero real: contar hipótesis vivas y resultados distintos
        n_hyp = int(st.get("n_hypotheses") or len(rivals) or 0)
        n_out = int(candidate.get("distinct_outcomes")
                    or st.get("distinct_outcomes") or 0)
        if n_hyp >= 2 and n_out >= 2:
            res = heuristic_eig(n_hyp, n_out)
            n_max = math.log2(n_hyp) or 1.0
            return min(1.0, res.eig / n_max), {"estimator": "heuristic_eig",
                                               **res.as_dict()}
    except Exception as exc:  # noqa: BLE001 - estimador roto ⇒ UNKNOWN honesto
        return None, {"estimator": "error", "detail": str(exc)[:120]}
    return None, {"estimator": "unavailable",
                  "why": "sin rivales cuantificables ni conteo de resultados"}


def historical_estimate(action: str, history: list[dict[str, Any]], *,
                        min_samples: int = 3) -> tuple[float | None, dict[str, Any]]:
    """Prior EMPÍRICO minado del historial (v0 auditable, sin ML).

    Mide la tasa de jugadas de esta acción que produjeron algo utilizable
    (veredicto informativo, refutación, evidencia) frente a las que no
    (fallo, presupuesto agotado, inconcluso). Con menos de `min_samples`
    observaciones devuelve **UNKNOWN**, nunca un número inventado."""
    rel = [h for h in history if h.get("action") == action]
    if len(rel) < min_samples:
        return None, {"estimator": "historical_v0", "n": len(rel),
                      "why": f"muestra insuficiente (<{min_samples})"}
    useful = 0
    for h in rel:
        s = str(h.get("summary") or "").lower()
        if h.get("error") or "falló" in s or "no disponible" in s:
            continue
        if any(k in s for k in ("refut", "contraejemplo", "verified", "proved",
                                "señal", "patrones", "encontr", "veredicto")):
            useful += 1
    rate = useful / len(rel)
    return rate, {"estimator": "historical_v0", "n": len(rel),
                  "useful": useful, "rate": round(rate, 3)}


def _clip(v: Any) -> float:
    """A [0,1], con guardas: NaN/Inf/None/no-numérico → 0.0 (jamás propagar)."""
    import math
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(f):
        return 0.0
    return max(0.0, min(1.0, f))


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


def _blend(proposer: float, mechanical: float | None, historical: float | None,
           *, w_mech: float = 0.65, w_hist: float = 0.20) -> float:
    """Mezcla las tres fuentes CONFIANDO MÁS en lo mecánico/histórico que en la
    autoevaluación del LLM (crítica externa aceptada). UNKNOWN no vota ni castiga:
    su peso se redistribuye — ausencia de cálculo ≠ evidencia de irrelevancia."""
    parts, weights = [proposer], [1.0 - (w_mech if mechanical is not None else 0.0)
                                  - (w_hist if historical is not None else 0.0)]
    if mechanical is not None:
        parts.append(mechanical)
        weights.append(w_mech)
    if historical is not None:
        parts.append(historical)
        weights.append(w_hist)
    total = sum(weights) or 1.0
    return sum(p * w for p, w in zip(parts, weights)) / total


def score(candidate: dict[str, Any], history: list[dict[str, Any]],
          state: dict[str, Any] | None = None, *,
          mode: str = "exploit") -> dict[str, Any]:
    """Puntúa UNA candidata con TRES fuentes separadas (nunca mezcladas en
    silencio) y devuelve el ActionScoreTrace completo.

    `mode`: 'exploit' (por defecto) maximiza utilidad esperada; 'explore' es el
    presupuesto reservado para ideas cuyo valor NO se puede estimar todavía —
    ahí la novedad pesa más y la falta de prior histórico NO castiga. Sin esto,
    el PolicyEngine se volvería policía de creatividad: mataría justo la jugada
    rara que abre una representación nueva (el riesgo que Merari señaló)."""
    action = str(candidate.get("action") or "")
    # --- proposer (LLM, declarado) --------------------------------------------
    p_info = _clip(candidate.get("info_esperada"))
    p_falsif = _clip(candidate.get("falsabilidad"))
    novedad = _clip(candidate.get("novedad"))
    incert = _clip(candidate.get("reduccion_incertidumbre"))
    riesgo_llm = _clip(candidate.get("riesgo"))
    # --- mechanical (calculado, el LLM no puede sobrescribirlo) ---------------
    m_info, info_trace = mechanical_information(candidate, state)
    m_falsif = MECHANICAL_FALSIFIABILITY.get(action)
    costo = ACTION_COST.get(action, 0.20)
    riesgo = max(ACTION_RISK.get(action, 0.10), riesgo_llm)
    # --- historical (minado del ledger; UNKNOWN si no hay muestra) ------------
    h_rate, hist_trace = historical_estimate(action, history)
    rep = _repetition_penalty(action, history)

    info = _blend(p_info, m_info, h_rate)
    falsif = _blend(p_falsif, m_falsif, None)
    w = dict(WEIGHTS)
    if mode == "explore":
        # exploración: la novedad manda y el costo pesa menos — es el presupuesto
        # deliberado para ideas de utilidad incierta pero potencial alto
        w["novedad"], w["info"], w["costo"] = 2.2, 0.8, 0.5
    utility = (w["info"] * info + w["falsif"] * falsif
               + w["novedad"] * novedad + w["incert"] * incert
               - w["costo"] * costo - w["riesgo"] * riesgo - rep)
    return {"action": action, "utility": round(utility, 4),
            "policy_version": POLICY_VERSION, "mode": mode,
            "desglose": {"info": round(info, 4), "falsif": round(falsif, 4),
                         "novedad": novedad, "incert": incert, "costo": costo,
                         "riesgo": riesgo, "repeticion": round(rep, 3)},
            "fuentes": SCORE_SOURCES,
            # ActionScoreTrace: cada señal con su valor, fuente y estimador
            "trace": {
                "information": {"proposer": p_info, "mechanical": m_info,
                                "historical": h_rate, "blended": round(info, 4),
                                **info_trace},
                "falsifiability": {"proposer": p_falsif, "mechanical": m_falsif,
                                   "blended": round(falsif, 4),
                                   "estimator": "structural_table"},
                "historical_prior": hist_trace,
                "weights": w}}


class PolicyEngine:
    """Administra ATENCIÓN y CÓMPUTO — no decide qué ideas están permitidas.

    Distinción deliberada (Merari, principio LEGO):
      * CreativeProposal — una idea. Puede ser rarísima, sin prior, sin
        información estimable. NO se rechaza aquí: se conserva.
      * ExecutionCandidate — la propuesta de GASTAR recursos en esa idea. Eso sí
        pasa por el scoring.
    Y reserva un `explore_ratio` del presupuesto para ideas de utilidad incierta:
    si siempre maximizas el valor esperado con lo que ya conoces, explotas el
    paradigma actual para siempre y nunca descubres una representación nueva.
    """

    def __init__(self, explore_ratio: float = 0.2) -> None:
        self._explore = max(0.0, min(1.0, explore_ratio))

    def _mode_for(self, history: list[dict[str, Any]]) -> str:
        """Determinista (nada de azar: rompe la reproducibilidad). Cada N-ésima
        jugada, según explore_ratio, se decide en modo EXPLORAR."""
        if self._explore <= 0:
            return "exploit"
        every = max(2, round(1.0 / self._explore))
        return "explore" if (len(history) + 1) % every == 0 else "exploit"

    def choose(self, candidates: list[dict[str, Any]],
               history: list[dict[str, Any]],
               state: dict[str, Any] | None = None
               ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """→ (candidata ganadora | None si no hay válidas, scores de todas)."""
        valid = [c for c in candidates
                 if isinstance(c, dict) and str(c.get("action") or "").strip()]
        if not valid:
            return None, []
        mode = self._mode_for(history)
        scored = [score(c, history, state, mode=mode) for c in valid]
        best_i = max(range(len(scored)), key=lambda i: scored[i]["utility"])
        winner = dict(valid[best_i])
        winner["_policy"] = {
            "elegida": scored[best_i], "todas": scored, "mode": mode,
            "regla": ("argmax utilidad; tres fuentes separadas "
                      "(proposer/mechanical/historical), UNKNOWN no castiga; "
                      f"modo {mode} (explore_ratio={self._explore})")}
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
                    "representacion": {
                        "type": "string",
                        "description": "solo reinterpretar: representación destino "
                                       "(matriz|grafo|booleano_sat|conjuntos|"
                                       "secuencia|modular) ('' si no)"},
                    "info_perdida": {
                        "type": "string",
                        "description": "solo reinterpretar: qué información NO "
                                       "sobrevive a la transformación ('' si no)"},
                    "distinct_outcomes": {
                        "type": "number",
                        "description": "cuántos RESULTADOS distinguibles puede dar "
                                       "esta jugada (alimenta el cálculo mecánico "
                                       "de información; 0 si no aplica)"},
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
