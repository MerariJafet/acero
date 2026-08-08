"""BOHR v2 — el director que DECIDE, no un guion fijo.

Antes el ciclo del Consejo era una secuencia cableada (Hipatia→Popper→Feynman→…).
Ahora Bohr conoce a sus 16 científicos y sus herramientas, mira el estado real de la
investigación después de CADA jugada, y decide como lo haría el humano que controla el
flujo: a quién llamar, si repetir con otros argumentos, si pedir la opinión hostil de
Aristóteles, si mandar a Ramanujan por una chispa cuando el camino directo se agotó,
si darle horas a Turing, si reformular y VOLVER A EMPEZAR, o si cerrar.

El tiempo no es restricción: el presupuesto de pared es de horas y cada ejecutor corre
lo que necesite. Las restricciones son EPISTÉMICAS (constitución de honestidad) y de
no-ciclarse (guard anti-bucle).

Honestidad (innegociable, embebida en el prompt y validada en código):
- Jamás declarar resuelto un problema abierto; disposiciones solo del conjunto honesto.
- La salida de un LLM no es evidencia; evidencia = ejecución verificada (Popper/Turing)
  o prueba mecánica (Gödel/Euclides). holds_empirically nunca asciende solo.
- Todo pase de estafeta queda registrado con su PORQUÉ (bitácora de decisiones).
"""
from __future__ import annotations

import time
from typing import Any, Callable

# disposiciones que Bohr puede declarar al cerrar — NUNCA "solved"/"proved" de un abierto
HONEST_DISPOSITIONS = ("needs_human_review", "refuted", "partial_progress",
                       "formally_supported", "holds_empirically", "dropped")

# el menú de jugadas: qué sabe hacer cada científico y CUÁNDO conviene llamarlo
ACTION_MENU: dict[str, dict[str, str]] = {
    "hipatia": {
        "hace": "busca en literatura real (OpenAlex/arXiv/Crossref) si ya está resuelto"
                " o si un lema logrado es NUEVO",
        "cuando": "SIEMPRE antes de gastar cómputo en una conjetura fresca; y al final,"
                  " para dictaminar la novedad de lo conseguido"},
    "popper": {
        "hace": "ataque computacional: busca contraejemplos con código verificado"
                " (formal-first, aritmética exacta)",
        "cuando": "conjetura falsable sin atacar aún, o tras una reformulación"},
    "feynman": {
        "hace": "interpreta el último resultado con actitud hacker: refina bordes,"
                " reformula, propone la segunda jugada",
        "cuando": "un ataque terminó y no es obvio qué sigue; o el enunciado es débil"},
    "godel": {
        "hace": "intento de PRUEBA mecánica (sympy/Z3) del enunciado o de un lema",
        "cuando": "el enunciado sobrevivió ataques y huele a demostrable, o hay un"
                  " sub-lema preciso"},
    "ramanujan": {
        "hace": "chispas laterales '¿y si…?' leyendo el catálogo de piezas (LEGO)",
        "cuando": "FRONTERA: los métodos directos están agotados o probados imposibles"},
    "turing": {
        "hace": "programa un experimento (instala piezas si faltan, Sage incluido),"
                " lo corre, repara y reintenta — presupuesto en MINUTOS que tú fijas",
        "cuando": "hay una idea concreta que necesita cómputo serio; dale tiempo"},
    "aristoteles": {
        "hace": "crítica hostil del estado actual (revisor adversarial)",
        "cuando": "antes de creerte un resultado; segunda opinión sobre lo que hay"},
    "kepler": {
        "hace": "cosecha anomalías de los datos del proyecto → hipótesis nuevas",
        "cuando": "hubo experimentos con discrepancias sin explicar"},
    "gauss": {
        "hace": "empaqueta dossier publicable (solo lo maduro, con límites explícitos)",
        "cuando": "hay un resultado verificado + novedad dictaminada"},
    "reiniciar": {
        "hace": "adopta un ENUNCIADO nuevo (tu 'statement') y vuelve a empezar el ataque",
        "cuando": "el enunciado actual se agotó pero la reformulación abre camino"},
    "cerrar": {
        "hace": "termina el ciclo con una disposición HONESTA y resumen",
        "cuando": "objetivo logrado, agotado, o toca decisión humana"},
}

DECIDE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string",
                   "description": "una jugada del menú: " + ", ".join(ACTION_MENU)},
        "reason": {"type": "string",
                   "description": "POR QUÉ esta jugada ahora (queda en la bitácora)"},
        "expected": {"type": "string",
                     "description": "qué esperas aprender/lograr con la jugada"},
        "statement": {"type": "string",
                      "description": "enunciado a usar ('' = mantener el actual); "
                                     "OBLIGATORIO si action=reiniciar"},
        "frontier": {"type": "string",
                     "description": "solo ramanujan: la frontera declarada ('' si no)"},
        "why_stuck": {"type": "string",
                      "description": "solo ramanujan: por qué está atorado ('' si no)"},
        "idea": {"type": "string",
                 "description": "solo turing: la idea/experimento a construir ('' si no)"},
        "piezas": {"type": "array", "items": {"type": "string"},
                   "description": "solo turing: piezas del TOOLBOX ([] si no)"},
        "budget_min": {"type": "number",
                       "description": "solo turing: minutos de presupuesto (0 = 60)"},
        "disposition": {"type": "string",
                        "description": "solo cerrar: " + " | ".join(HONEST_DISPOSITIONS)
                                       + " ('' si no)"},
    },
    "required": ["action", "reason", "expected", "statement", "frontier", "why_stuck",
                 "idea", "piezas", "budget_min", "disposition"],
    "additionalProperties": False,
}

_BOHR_SYS = """Eres Niels Bohr dirigiendo el Consejo de ACERO — el investigador autónomo.
Tu papel: el humano que controla el flujo. Miras el ESTADO real (historial de jugadas y
sus resultados VERIFICADOS) y eliges la SIGUIENTE jugada del menú. Piensas en términos
de: ¿qué sé ya? ¿qué me falta saber? ¿quién del Consejo me lo consigue más directo?

Estilo de dirección (como un gran director humano):
- Repite una jugada SOLO con argumentos distintos (otro ángulo, otro presupuesto).
- Pide segunda opinión (aristoteles) antes de creerte cualquier resultado positivo.
- Si el camino directo está agotado o PROBADO imposible, no insistas: ramanujan.
- Una chispa prometedora merece cómputo de verdad: turing con budget_min generoso.
- Un lema logrado no vale nada sin novedad: hipatia lo dictamina ANTES de gauss.
- Reformular está permitido (reiniciar) — abandona enunciados muertos sin nostalgia.
- El tiempo NO es restricción; la deshonestidad SÍ. Cierra solo con disposición honesta.

CONSTITUCIÓN (innegociable):
- JAMÁS declares resuelto un problema abierto. La validación final es HUMANA.
- Texto de LLM no es evidencia. Evidencia = ejecución verificada o prueba mecánica.
- Si nada maduró, 'needs_human_review' es un cierre digno — inflar es el único fracaso."""


class BohrOrchestrator:
    """Bucle decidir→ejecutar→observar con ejecutores inyectables (tests offline)."""

    def __init__(self, provider: Any, executors: dict[str, Callable[..., dict]], *,
                 knowledge: str = "", max_actions: int = 24,
                 wall_budget_s: float = 8 * 3600.0,
                 on_step: Callable[[str, dict, dict], None] | None = None) -> None:
        self._provider = provider
        self._ex = executors
        self._knowledge = knowledge
        self._max = max_actions
        self._wall = wall_budget_s
        self._on_step = on_step

    # --- contexto que ve Bohr en cada decisión --------------------------------------
    def _context(self, statement: str, history: list[dict[str, Any]],
                 t0: float) -> str:
        menu = "\n".join(f"- {k}: {v['hace']}. Cuándo: {v['cuando']}"
                         for k, v in ACTION_MENU.items())
        hist = "\n".join(
            f"{i+1}. [{h['action']}] {h.get('reason', '')[:100]} → "
            f"{str(h.get('summary', ''))[:220]}"
            for i, h in enumerate(history)) or "(sin jugadas aún)"
        left = max(0, int(self._wall - (time.time() - t0)))
        return (f"{_BOHR_SYS}\n\nMENÚ DE JUGADAS:\n{menu}\n\n"
                f"TU CONSEJO Y SUS HERRAMIENTAS:\n{self._knowledge}\n\n"
                f"ENUNCIADO ACTUAL:\n{statement}\n\n"
                f"HISTORIAL (jugada → resultado REAL):\n{hist}\n\n"
                f"Presupuesto restante: {left // 60} min de pared, "
                f"{self._max - len(history)} jugadas.\n"
                "Decide la SIGUIENTE jugada.")

    def _decide(self, statement: str, history: list[dict[str, Any]],
                t0: float) -> dict[str, Any]:
        last_err = ""
        for _ in range(3):
            try:
                d = self._provider.complete_json(
                    self._context(statement, history, t0) + last_err,
                    DECIDE_SCHEMA, temperature=0.4)
            except Exception as exc:  # noqa: BLE001
                return {"action": "cerrar", "reason": f"proveedor caído: {exc}",
                        "disposition": "needs_human_review"}
            act = str(d.get("action") or "")
            if act in ACTION_MENU:
                return d
            last_err = (f"\n\nERROR: '{act}' no está en el menú. Elige una jugada "
                        f"válida de: {', '.join(ACTION_MENU)}.")
        return {"action": "cerrar", "reason": "no eligió jugada válida en 3 intentos",
                "disposition": "needs_human_review"}

    # --- el bucle del director --------------------------------------------------------
    def run(self, claim: str) -> dict[str, Any]:
        t0 = time.time()
        statement = claim
        history: list[dict[str, Any]] = []
        disposition, close_reason = "needs_human_review", "presupuesto agotado"
        while len(history) < self._max and (time.time() - t0) < self._wall:
            d = self._decide(statement, history, t0)
            act = d["action"]
            if act == "cerrar":
                disp = str(d.get("disposition") or "")
                disposition = disp if disp in HONEST_DISPOSITIONS else "needs_human_review"
                close_reason = str(d.get("reason") or "")
                if self._on_step:
                    self._on_step(act, d, {"summary": close_reason})
                break
            if act == "reiniciar":
                new_stmt = str(d.get("statement") or "").strip()
                entry = {"action": act, "reason": d.get("reason", ""),
                         "summary": (f"nuevo enunciado adoptado: {new_stmt[:150]}"
                                     if new_stmt else
                                     "reinicio SIN enunciado nuevo — ignorado")}
                if new_stmt:
                    statement = new_stmt
                history.append(entry)
                if self._on_step:
                    self._on_step(act, d, entry)
                continue
            # guard anti-bucle: 3 repeticiones consecutivas con el mismo resultado
            same = [h for h in history[-3:] if h["action"] == act]
            if len(same) == 3 and len({str(h.get("summary"))[:80] for h in same}) == 1:
                history.append({"action": act, "reason": d.get("reason", ""),
                                "summary": "BLOQUEADO por anti-bucle: 3 repeticiones "
                                           "idénticas — Bohr debe cambiar de jugada"})
                continue
            ex = self._ex.get(act)
            if ex is None:
                history.append({"action": act, "reason": d.get("reason", ""),
                                "summary": f"ejecutor '{act}' no disponible"})
                continue
            try:
                res = ex(statement=statement, decision=d) or {}
            except Exception as exc:  # noqa: BLE001 - una jugada rota no mata el ciclo
                res = {"summary": f"la jugada falló: {str(exc)[:160]}", "error": True}
            if res.get("statement"):                    # feynman puede refinar
                statement = str(res["statement"])
            history.append({"action": act, "reason": d.get("reason", ""),
                            "summary": res.get("summary", ""),
                            "verdict": res.get("verdict", "")})
            if self._on_step:
                self._on_step(act, d, res)
        return {"disposition": disposition, "close_reason": close_reason,
                "statement": statement, "history": history,
                "n_actions": len(history),
                "elapsed_s": round(time.time() - t0, 1)}


def build_knowledge() -> str:
    """El conocimiento que Bohr tiene de su Consejo: personajes + piezas LEGO reales."""
    from ..portal.council import PERSONAS
    from .toolbox import catalog_text
    ppl = "\n".join(f"- {p['name']} ({p['id']}): {p['role']} — {p['summary'][:110]}"
                    for p in PERSONAS)
    return f"PERSONAJES:\n{ppl}\n\nPIEZAS (TOOLBOX):\n{catalog_text()}"
