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
    "noether": {
        "hace": "arbitraje experto de teoría de números: revisa el resultado como"
                " referee de journal (teorema vs evidencia vs conjetura, novedad,"
                " chequeos faltantes) — arbitraje INTERNO, no validación externa",
        "cuando": "hay un resultado maduro que aspira a nota publicable; ANTES de"
                  " gauss y del experto humano"},
    "reinterpretar": {
        "hace": "CAMBIA LA MIRADA, no el problema: propone otra representación"
                " matemáticamente válida del MISMO objeto (matriz binaria, grafo"
                " bipartito, restricciones booleanas/SAT, sistema de conjuntos,"
                " secuencia de excepciones, clases modulares…) y declara qué"
                " información se preserva y cuál se pierde. Habilita herramientas"
                " de OTRA rama sobre el mismo problema",
        "cuando": "el ataque directo se repite sin avanzar, o sospechas que la"
                  " estructura es invisible en la representación actual. La Ronda 4"
                  " ejecutó todo bien sobre la mirada equivocada: esta jugada existe"
                  " para eso. NO cambia la premisa sellada — solo cómo se mira"},
    "rivales": {
        "hace": "genera TEORÍAS RIVALES explícitas para un patrón/conjetura"
                " (mecanismo directo, inverso, causa común, artefacto de"
                " selección/medición, explicación nula) antes de creerle",
        "cuando": "hay un patrón o resultado positivo SIN alternativas"
                  " descartadas — obligatorio antes de madurar hacia gauss"},
    "discriminar": {
        "hace": "diseña el experimento que MÁS separa a las rivales vivas:"
                " calcula qué resultado esperaría cada una y elige el que"
                " maximiza el desacuerdo (ganancia de información real)",
        "cuando": "existen ≥2 rivales con predicciones distinguibles; es la"
                  " jugada más informativa por unidad de cómputo cuando aplica"},
    "mendeleev": {
        "hace": "busca ESTRUCTURA en los datos verificados del proyecto: deriva"
                " representaciones (log, razones, módulos), detecta correlaciones,"
                " invariantes aproximados y LEYES simbólicas sencillas (y≈a·x^b…)."
                " Devuelve PatternCandidates: patrón ≠ descubrimiento, causalidad NO"
                " establecida, con rivales H1-H4 y procedencia reproducible",
        "cuando": "hay una tabla de observaciones (≥5 filas) y la pregunta es '¿qué"
                  " estructura hay aquí?' — p.ej. buscar la fórmula de una ley de"
                  " crecimiento o de una llave dinámica. NO para probar teoremas ni"
                  " con 3 datos"},
    "euler": {
        "hace": "barrido masivo en PARALELO: genera N candidatas alrededor del"
                " enunciado, las filtra por novedad+EVA concurrentemente, aprueba"
                " las sobrevivientes y les lanza misiones",
        "cuando": "la pregunta admite muchas variantes atacables y conviene explorar"
                  " en ANCHO, no en profundidad; o el ataque directo a UNA sola"
                  " formulación ya se agotó"},
    "davinci": {
        "hace": "divergencia dirigida: propone y CORRE varios enfoques distintos del"
                " mismo objetivo (math_explorer), aprende de los que fallan y"
                " sintetiza una hipótesis de los viables — con guardas de consenso",
        "cuando": "el camino directo se repite sin avanzar; ANTES de rendirte o"
                  " reformular, mira el problema desde 3-5 ángulos ejecutables"},
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
        "dataset_ref": {"type": "string",
                        "description": "solo mendeleev: ruta bajo research/ a un JSON "
                                       "con la lista de filas a analizar ('' = usar "
                                       "los datos numéricos del ledger del proyecto)"},
        "target": {"type": "string",
                   "description": "solo mendeleev: columna objetivo para buscar una "
                                  "ley y=f(x) ('' = solo correlaciones/invariantes)"},
        "representacion": {
            "type": "string",
            "description": "solo reinterpretar: la representación destino "
                           "(matriz | grafo | booleano_sat | conjuntos | "
                           "secuencia | modular | geometrico) ('' si no)"},
        "info_perdida": {
            "type": "string",
            "description": "solo reinterpretar: qué información NO sobrevive a la "
                           "transformación — declararlo es obligatorio ('' si no)"},
        "n_sweep": {"type": "number",
                    "description": "solo euler: cuántas candidatas barrer (0 = 8)"},
        "approaches": {"type": "number",
                       "description": "solo davinci: cuántos enfoques divergir (0 = 4)"},
    },
    "required": ["action", "reason", "expected", "statement", "frontier", "why_stuck",
                 "idea", "piezas", "budget_min", "disposition", "dataset_ref",
                 "target", "representacion", "info_perdida", "n_sweep", "approaches"],
    "additionalProperties": False,
}

_BOHR_SYS = """Eres Niels Bohr dirigiendo el Consejo de ACERO — el investigador autónomo.
Tu papel: el humano que controla el flujo. Miras el ESTADO real (historial de jugadas y
sus resultados VERIFICADOS) y eliges la SIGUIENTE jugada del menú. Piensas en términos
de: ¿qué sé ya? ¿qué me falta saber? ¿quién del Consejo me lo consigue más directo?

FINALIDAD ÚLTIMA (por encima de cualquier jugada individual): el programa existe para
ENCONTRAR CONOCIMIENTO NUEVO, no para repetir o confirmar el que ya existe. Cada
personaje del Consejo es una PIEZA — hipatia busca, gauss prueba, turing computa,
ramanujan especula, mendeleev encuentra patrones, gödel verifica mecánicamente. Tu
trabajo de director no es escoger UNA pieza a la vez por inercia: es COMBINARLAS de
formas que nadie ha probado todavía, como piezas de lego, hasta dar con una
combinación que abra una puerta que estaba cerrada. Si dos jugadas seguidas usan el
mismo personaje con el mismo ángulo, pregúntate qué combinación distinta darías si
pensaras en el catálogo completo (TOOLBOX) en vez de en el último resultado.

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
                 knowledge: str = "", max_actions: int = 200,
                 wall_budget_s: float = 7 * 86400.0,
                 on_step: Callable[[str, dict, dict], None] | None = None,
                 on_think: Callable[[int, int], None] | None = None,
                 on_restart: Callable[[str], str] | None = None,
                 policy: Any = "default",
                 state_provider: Callable[[], dict] | None = None) -> None:
        self._provider = provider
        self._ex = executors
        self._knowledge = knowledge
        self._max = max_actions
        self._wall = wall_budget_s
        self._on_step = on_step
        # on_think(intento, n_jugadas_previas): se dispara ANTES de cada llamada al
        # LLM que decide la jugada. Es el único latido durante ese tramo, que puede
        # durar horas — sin él, "pensando" es indistinguible de "colgado".
        self._on_think = on_think
        # on_restart(nuevo_enunciado) -> advertencia|"" : el guardián de premisa.
        # 'reiniciar' es LA jugada que cambia el enunciado — el punto exacto donde
        # las definiciones se degradaron en silencio entre las rondas 2 y 3 de
        # Erdős–Straus. La advertencia se anexa al historial para que Bohr la VEA.
        self._on_restart = on_restart
        # policy: "default" = PolicyEngine estándar (Bohr híbrido v3); None =
        # decisión única clásica (tests/legado); o un engine inyectado.
        if policy == "default":
            from .policy import PolicyEngine
            self._policy: Any = PolicyEngine()
        else:
            self._policy = policy
        # state_provider() -> {rivals, n_hypotheses, …}: lo que el PolicyEngine
        # necesita para CALCULAR información esperada en vez de creerle al LLM
        self._state_provider = state_provider

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
        # --- BOHR HÍBRIDO (v3): el LLM PROPONE candidatas, la máquina ELIGE ---------
        # Crítica externa aceptada: un LLM como estratega con poder absoluto es el
        # mayor riesgo del sistema. Bohr propone 2-4 jugadas alternativas con sus
        # estimaciones; el PolicyEngine las puntúa con señales que el LLM no
        # controla (costos por tabla, riesgo, repetición MEDIDA en el historial) y
        # el desglose queda en la decisión. Si la propuesta múltiple falla, cae al
        # camino clásico de decisión única — nunca se queda sin jugada por esto.
        last_err = ""
        attempts_done = 0
        if self._policy is not None:
            if self._on_think:
                try:
                    self._on_think(1, len(history))
                except Exception:  # noqa: BLE001
                    pass
            try:
                from .policy import PROPOSE_SCHEMA
                prop = self._provider.complete_json(
                    self._context(statement, history, t0)
                    + "\n\nPropón de 2 a 4 jugadas CANDIDATAS que compitan de "
                      "verdad (estrategias distintas), con tus estimaciones "
                      "honestas 0-1. Un motor de política elegirá — tu trabajo "
                      "es dar alternativas reales, no una favorita disfrazada.",
                    PROPOSE_SCHEMA, temperature=0.5)
            except Exception as exc:  # noqa: BLE001
                return {"action": "cerrar", "reason": f"proveedor caído: {exc}",
                        "disposition": "needs_human_review"}
            if isinstance(prop, dict) and "candidatas" in prop:
                cands = [c for c in (prop.get("candidatas") or [])
                         if str(c.get("action") or "") in ACTION_MENU]
                st = None
                if self._state_provider:
                    try:
                        st = self._state_provider()
                    except Exception:  # noqa: BLE001 - estado roto ⇒ sin mecánico
                        st = None
                winner, _scored = self._policy.choose(cands, history, st)
                if winner is not None:
                    return winner
                attempts_done = 1          # propuesta sin candidata válida
            elif isinstance(prop, dict):
                # proveedor de decisión única (tests/legado): su respuesta cuenta
                # como el PRIMER intento — válida se respeta, inválida se corrige
                act = str(prop.get("action") or "")
                if act in ACTION_MENU:
                    return prop
                last_err = (f"\n\nERROR: '{act}' no está en el menú. Elige una "
                            f"jugada válida de: {', '.join(ACTION_MENU)}.")
                attempts_done = 1
        for intento in range(attempts_done, 3):
            # LATIDO: pensar la jugada es una llamada al LLM que puede tardar HORAS
            # (techo de 3600s, hasta 3 intentos). Sin esta señal el tablero se queda
            # congelado en la etiqueta del último ejecutor y un ciclo perfectamente
            # sano parece colgado. No es un límite de tiempo — solo visibilidad.
            if self._on_think:
                try:
                    self._on_think(intento + 1, len(history))
                except Exception:  # noqa: BLE001 - el latido nunca rompe el ciclo
                    pass
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
                    if self._on_restart:
                        try:
                            warn = self._on_restart(new_stmt)
                        except Exception:  # noqa: BLE001 - guardián roto ≠ bloquear
                            warn = ""
                        if warn:
                            entry["summary"] += f" | {warn}"
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


# --- dictamen del backlog de propuestas ---------------------------------------
# Bohr es quien dirige: cuando el backlog de hipótesis PROPOSED crece (las dejan
# sus propios ciclos, la máquina de anomalías, los personajes creativos), es ÉL
# quien juzga cuáles prometen y cuáles no — no una regla ciega de antigüedad.
# Patrón de la casa: el LLM PROPONE el ranking con razones, la máquina ACOTA
# (valida ids, completa faltantes, aplica el tope). Sin LLM, cae a un orden
# razonable (más recientes primero) para que el dictamen NUNCA se detenga.

DICTAMEN_SCHEMA = {
    "type": "object",
    "properties": {
        "ranked": {"type": "array", "items": {"type": "string"}},
        "drop_reasons": {"type": "object"},
    },
    "required": ["ranked"],
    "additionalProperties": False,
}


def dictamen_backlog(pool: list[dict], cap: int, *, provider: Any = None) -> dict:
    """Rankea el backlog de propuestas de más a menos prometedora (juicio de Bohr).

    Devuelve {"ranked": [ids mejor→peor], "reasons": {id: por qué queda fuera},
    "via": "bohr_llm"|"fallback"}. El que llama decide qué hacer con el orden
    (adoptar las primeras, rechazar las que exceden el tope)."""
    order = sorted(pool, key=lambda h: str(h.get("created_at") or h.get("id") or ""),
                   reverse=True)
    fallback = [str(h.get("id")) for h in order if h.get("id")]
    ok = provider is not None and getattr(provider, "available", lambda: False)()
    if ok and len(fallback) > 1:
        try:
            listing = "\n".join(
                f"- {h.get('id')} [{h.get('tag') or '?'}] "
                f"{str(h.get('claim') or h.get('title') or '')[:110]}"
                for h in order[:60])
            prompt = (
                _BOHR_SYS
                + "\n\nDICTAMEN DE BACKLOG. Estas propuestas de hipótesis llevan "
                  "tiempo sin que nadie las adjudique. Ranquéalas de MÁS a MENOS "
                  "prometedora para encontrar conocimiento NUEVO: falsable, no "
                  "trivial, no redundante con las demás, con un ángulo que el "
                  "proyecto no haya corrido ya. Solo las primeras "
                + str(max(1, cap))
                + " sobrevivirán; para las que dejes fuera da una razón de UNA "
                  "línea (drop_reasons: id → razón). Devuelve TODOS los ids.\n\n"
                + listing)
            out = provider.complete_json(prompt, DICTAMEN_SCHEMA, temperature=0.2)
            valid = set(fallback)
            ranked = [i for i in (out.get("ranked") or []) if i in valid]
            ranked += [i for i in fallback if i not in set(ranked)]
            reasons = {str(k): str(v)[:200]
                       for k, v in (out.get("drop_reasons") or {}).items()
                       if str(k) in valid}
            return {"ranked": ranked, "reasons": reasons, "via": "bohr_llm"}
        except Exception:  # noqa: BLE001 - el dictamen nunca se detiene por el LLM
            pass
    return {"ranked": fallback, "reasons": {}, "via": "fallback"}
