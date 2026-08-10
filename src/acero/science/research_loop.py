"""ResearchLoop — el salto de "asistente que testea" a INVESTIGADOR.

Antes: generar → probar → refutar/conservar, y parar. Un investigador humano hace una
SEGUNDA JUGADA: ve que "falla trivial en n=1", excluye el borde y ataca el núcleo; ve un
superviviente y en vez de más fuerza bruta intenta PROBARLO o entender por qué se cumple.

El corazón de este loop es el filtro **ACTITUD HUMANA** (`HumanAttitude`): una chispa
creativa que OBSERVA como un matemático astuto con mentalidad de hacker —para DESCUBRIR,
no para romper— y propone las opciones que la máquina no ve: refinar un borde, reformular,
fortalecer, cambiar el cuantificador, buscar el patrón, intentar una demostración.

El loop compone lo ya construido:
    conjetura
      → PROBAR (MathProbe + guardas anti-refutación-falsa)
      → ACTITUD HUMANA (¿trivial? ¿otra forma? ¿probar? ¿fortalecer?)
      → actuar (refinar y reintentar / intentar prueba / escalar a humano)
      → persistir (ledger) y disponer

Honestidad: la creatividad genera IDEAS y mejores enunciados; los VEREDICTOS siguen
saliendo del probador y sus guardas. La actitud humana nunca "declara" un resultado.
Todo (provider/prober/explorer/ledger) es inyectable para tests offline.
"""

from __future__ import annotations

from typing import Any

HUMAN_ATTITUDE_SCHEMA = {
    "type": "object",
    "properties": {
        "observation": {"type": "string"},          # qué nota un humano astuto
        "verdict_is_trivial": {"type": "boolean"},   # ¿el resultado es borde/degenerado?
        "refined_statement": {"type": "string"},     # enunciado más filoso (o "")
        "alternative_angles": {"type": "array", "items": {"type": "string"}},
        "next_action": {"type": "string"},           # ver _ACTIONS
    },
    "required": ["observation", "verdict_is_trivial", "refined_statement",
                 "alternative_angles", "next_action"],
    "additionalProperties": False,
}

_ACTIONS = ("refine_and_retry", "strengthen_and_retry", "attempt_proof",
            "escalate_to_human", "drop")

_HUMAN_ATTITUDE_SYS = (
    "Eres ACTITUD HUMANA: la chispa creativa de ACERO. NO ejecutas cálculos; OBSERVAS "
    "como un matemático astuto con mentalidad de HACKER —para DESCUBRIR opciones que aún "
    "no se ven, no para romper—. Te doy una conjetura y QUÉ pasó al atacarla "
    "computacionalmente. Ve lo que la máquina no ve:\n"
    " • Si la refutación es TRIVIAL (un borde como n=1, un caso degenerado, una hipótesis "
    "que nadie querría): dilo (verdict_is_trivial=true) y da un refined_statement que "
    "EXCLUYA el borde y conserve el núcleo interesante.\n"
    " • Si SOBREVIVIÓ a muchas pruebas: propón una jugada de investigador — intentar una "
    "DEMOSTRACIÓN (¿hay estructura, inducción, biyección, invariante?), o una versión MÁS "
    "FUERTE que sea más fértil, o un ángulo no probado.\n"
    "Sé concreto y creativo: reformula, cambia el cuantificador, añade/quita una hipótesis, "
    "busca el patrón oculto. Da observation, verdict_is_trivial, refined_statement (o \"\"), "
    "alternative_angles (lista breve), y next_action ∈ {refine_and_retry, "
    "strengthen_and_retry, attempt_proof, escalate_to_human, drop}."
)

_SKETCH_SYS = (
    "Eres un demostrador de ACERO con actitud humana. Da un BOCETO de demostración honesto "
    "para esta afirmación (idea central: inducción, biyección, invariante, principio de "
    "casillas, etc.), señalando qué faltaría para cerrarlo. NO afirmes que está demostrado. "
    "Sé breve y concreto."
)

# --- cerrar el ciclo: reducir el boceto a un LEMA verificable simbólicamente ------
FORMALIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "lemma": {"type": "string"},          # el hecho clave, en palabras
        "reduction": {"type": "string"},      # por qué probar el lema cierra el argumento
        "formal_claim": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"}, "lhs": {"type": "string"},
                "rhs": {"type": "string"}, "expr": {"type": "string"},
                "var": {"type": "string"}, "to": {"type": "string"},
                "expected": {"type": "string"}, "term": {"type": "string"},
                "index": {"type": "string"}, "lower": {"type": "string"},
                "upper": {"type": "string"}, "closed": {"type": "string"}},
            "required": ["kind", "lhs", "rhs", "expr", "var", "to", "expected",
                         "term", "index", "lower", "upper", "closed"],
            "additionalProperties": False},
        # Gödel (Z3/SMT): for LOGIC / COUNTING / quantified claims over ints or booleans
        "z3_claim": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},          # int_forall|bool_forall|int_exists|""
                "expr": {"type": "string"},          # relation over the declared vars
                "vars": {"type": "array", "items": {"type": "string"}},
                "assume": {"type": "array", "items": {"type": "string"}},
                "sort": {"type": "string"}},         # int|real|bool
            "required": ["kind", "expr", "vars", "assume", "sort"],
            "additionalProperties": False},
    },
    "required": ["lemma", "reduction", "formal_claim", "z3_claim"],
    "additionalProperties": False,
}

_FORMALIZE_SYS = (
    "Eres el FORMALIZADOR de ACERO. Te doy una afirmación y un boceto/reducción. Extrae el "
    "LEMA NÚCLEO que sostenga el argumento y exprésalo en el motor adecuado:\n"
    "• formal_claim (sympy, para ÁLGEBRA/ANÁLISIS): identity con lhs/rhs; inequality con "
    "expr/var; limit con expr/var/to/expected; boolean con expr; summation/product con "
    "term/index/lower/upper/closed. Rellena SOLO los campos del kind; los demás en \"\".\n"
    "• z3_claim (Z3/SMT, para LÓGICA/CONTEO/cuantificadores sobre enteros o booleanos, "
    "p.ej. 'para todo entero n con tales restricciones se cumple X', o argumentos de "
    "casillas): kind int_forall|bool_forall|int_exists; expr (relación con operadores "
    "And/Or/Not/Implies/If/Sum y == <= >= sobre las variables); vars (lista de nombres); "
    "assume (hipótesis); sort int|real|bool. Usa ESTE cuando sympy no aplique (¡el conteo "
    "combinatorio va aquí!).\n"
    "EJEMPLO de z3_claim (conteo tipo casillas): para 'en m casillas sin dos marcas "
    "adyacentes hay a lo sumo ceil(m/2) marcas', con m fijo (p.ej. m=9): "
    "{kind:'bool_forall', sort:'bool', vars:['d0','d1','d2','d3','d4','d5','d6','d7','d8'], "
    "assume:[], expr:'Implies(And(Not(And(d0,d1)),Not(And(d1,d2)),Not(And(d2,d3)),"
    "Not(And(d3,d4)),Not(And(d4,d5)),Not(And(d5,d6)),Not(And(d6,d7)),Not(And(d7,d8))), "
    "Sum([If(d0,1,0),If(d1,1,0),If(d2,1,0),If(d3,1,0),If(d4,1,0),If(d5,1,0),If(d6,1,0),"
    "If(d7,1,0),If(d8,1,0)]) <= 5)'}. Si el enunciado tiene un rango acotado de n, ELIGE el "
    "caso MAYOR como representativo y codifícalo así.\n"
    "Elige UN motor (el otro déjalo con kind=\"\"). Si nada se reduce, ambos kind=\"\". "
    "Da también reduction: por qué probar ese lema cerraría la afirmación."
)

# --- AMBICIÓN: ante un problema ABIERTO, buscar una contribución PARCIAL demostrable ---
# Reutiliza los sub-esquemas formal_claim/z3_claim del formalizador (Codex-compatibles).
CONTRIB_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string"},          # necessary_condition|bound|variant|none
        "statement": {"type": "string"},     # la contribución en palabras
        "why_partial": {"type": "string"},   # por qué es progreso pero NO la solución
        "formal_claim": FORMALIZE_SCHEMA["properties"]["formal_claim"],
        "z3_claim": FORMALIZE_SCHEMA["properties"]["z3_claim"],
    },
    "required": ["kind", "statement", "why_partial", "formal_claim", "z3_claim"],
    "additionalProperties": False,
}

_CONTRIB_SYS = (
    "Eres la SEGUNDA JUGADA de ACERO ante un problema probablemente ABIERTO. La conjetura "
    "sobrevivió a la búsqueda de contraejemplos pero NO está demostrada. Como investigador "
    "honesto, propón UNA contribución PARCIAL y DEMOSTRABLE (no resuelve el problema, pero es "
    "progreso real y verificable):\n"
    "• necessary_condition: una propiedad que CUALQUIER contraejemplo DEBE cumplir (acota "
    "dónde buscar; p.ej. 'todo contraejemplo n es libre de cuadrados' o 'divisible por…').\n"
    "• bound: una cota demostrable relacionada.\n"
    "• variant: una versión más débil o un caso particular que SÍ se pueda probar.\n"
    "Exprésala para VERIFICARLA mecánicamente en formal_claim (sympy) o z3_claim (Z3), igual "
    "que el formalizador: rellena SOLO el motor que uses; el otro con kind=\"\". Si no se te "
    "ocurre nada demostrable, kind='none' y ambos claim kind=\"\". Da statement (en palabras) "
    "y why_partial (por qué es progreso pero NO la solución). NUNCA afirmes que resolviste el "
    "problema abierto: sólo propones un resultado parcial verificable."
)


class HumanAttitude:
    """El filtro creativo. Reutilizable: se le puede dar SIEMPRE esta actitud."""

    def __init__(self, *, provider: Any = None) -> None:
        self._provider = provider

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        return CodexCliProvider()

    def observe(self, statement: str, probe_result: dict[str, Any],
                trail: list[dict[str, Any]]) -> dict[str, Any]:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return {"observation": "", "verdict_is_trivial": False,
                    "refined_statement": "", "alternative_angles": [],
                    "next_action": "escalate_to_human"}
        ctx = (f"CONJETURA: {statement}\n"
               f"RESULTADO DEL ATAQUE: veredicto={probe_result.get('verdict')}; "
               f"contraejemplo={probe_result.get('counterexample')}; "
               f"casos_probados={probe_result.get('n_tested')}; "
               f"detalle={str(probe_result.get('detail'))[:200]}")
        if trail:
            ctx += f"\nJUGADAS PREVIAS: {[t.get('next_action') for t in trail]}"
        out = prov.complete_json(f"{_HUMAN_ATTITUDE_SYS}\n\n{ctx}",
                                 HUMAN_ATTITUDE_SCHEMA, temperature=0.7)
        if not isinstance(out, dict):
            return {"observation": "", "verdict_is_trivial": False,
                    "refined_statement": "", "alternative_angles": [],
                    "next_action": "escalate_to_human"}
        act = out.get("next_action")
        if act not in _ACTIONS:
            out["next_action"] = "escalate_to_human"
        return out


class ResearchLoop:
    def __init__(self, *, provider: Any = None, prober: Any = None, attitude: Any = None,
                 explorer: Any = None, ledger: Any = None, max_depth: int = 3,
                 on_event: Any = None) -> None:
        self._provider = provider
        self._prober = prober
        self._attitude = attitude
        self._explorer = explorer
        self._ledger = ledger
        self._max_depth = max(1, max_depth)
        self._on_event = on_event      # observador opcional (estado EN VIVO del portal)

    def _emit(self, event: str, **kw: Any) -> None:
        if self._on_event is None:
            return
        try:
            self._on_event({"event": event, **kw})
        except Exception:  # noqa: BLE001 - un observador roto jamás detiene el loop
            pass

    # --- injectable primitives ------------------------------------------------
    def _probe(self, statement: str) -> dict[str, Any]:
        if self._prober is not None:
            return self._prober(statement)
        from .math_probe import MathProbe, _FileScriptCache
        # EFICIENCIA: formal-first (sympy/Z3 gratis antes del codegen) + caché de
        # scripts buenos de Tycho (ronda 1 gratis al reintentar el mismo claim)
        r = MathProbe(provider=self._provider,
                      script_cache=_FileScriptCache()).probe(statement, max_tries=2)
        comp = r.get("computational") or {}
        return {"verdict": r.get("verdict"), "detail": r.get("detail"),
                "counterexample": comp.get("counterexample"),
                "n_tested": comp.get("n_tested")}

    def _observe(self, statement: str, probe: dict[str, Any],
                 trail: list[dict[str, Any]]) -> dict[str, Any]:
        att = self._attitude or HumanAttitude(provider=self._provider)
        if callable(att):
            return att(statement, probe, trail)
        return att.observe(statement, probe, trail)

    def _can_llm(self) -> bool:
        """Whether the loop may run an LLM 'second move'. An explicit provider is used iff
        available; when none is injected we only auto-create Codex in FULL-AUTO mode (no
        injected prober) — so offline tests that inject a prober stay deterministic and
        never spin up a real provider."""
        prov = self._provider
        if prov is not None:
            return bool(getattr(prov, "available", lambda: False)())
        return self._prober is None

    def _sketch(self, statement: str) -> str:
        prov = self._provider
        if prov is None:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return ""
        try:
            return prov.complete(f"{_SKETCH_SYS}\n\nAFIRMACIÓN: {statement}",
                                 temperature=0.4, max_tokens=700).text.strip()[:1200]
        except Exception:  # noqa: BLE001
            return ""

    def _record(self, statement: str, result: dict[str, Any]) -> None:
        if self._ledger is None:
            return
        try:
            self._ledger.record(statement, {
                "status": result.get("disposition"),
                "verdict": result.get("final_verdict"),
                "hypothesis": result.get("final_statement"),
                "viable_approaches": []})
        except Exception:  # noqa: BLE001
            pass

    # --- the investigator loop ------------------------------------------------
    def investigate(self, statement: str, *, max_depth: int | None = None) -> dict[str, Any]:
        depth_cap = max_depth or self._max_depth
        trail: list[dict[str, Any]] = []
        current = statement
        disposition = "inconclusive"
        final_verdict = None
        sketch = ""
        formal_support: dict[str, Any] | None = None
        lemma: str | None = None
        contributions: list[dict[str, Any]] = []
        for depth in range(depth_cap):
            self._emit("probing", depth=depth + 1, max=depth_cap, statement=current)
            probe = self._probe(current)
            v = probe.get("verdict")
            final_verdict = v
            self._emit("deciding", depth=depth + 1, max=depth_cap, statement=current,
                       verdict=v)
            att = self._observe(current, probe, trail)
            action = att.get("next_action", "escalate_to_human")
            trail.append({
                "depth": depth + 1, "statement": current, "verdict": v,
                "counterexample": probe.get("counterexample"),
                "n_tested": probe.get("n_tested"),
                "observation": att.get("observation"),
                "trivial": bool(att.get("verdict_is_trivial")),
                "alternative_angles": att.get("alternative_angles") or [],
                "next_action": action,
            })
            if v == "verified":
                disposition = "verified"
                break
            # --- the human 'second move' on a refutation --------------------------
            if v == "refuted":
                refined = (att.get("refined_statement") or "").strip()
                # honor the creative move whenever the attitude proposes a *different*
                # sharpened statement (a boundary exclusion, a fixed hypothesis, a
                # reorientation) — not only on a strictly 'trivial' flag.
                if action == "refine_and_retry" and refined and refined != current:
                    current = refined
                    self._emit("retry", depth=depth + 2, max=depth_cap, statement=current)
                    continue                      # attack the sharpened core
                disposition = "refuted"
                break
            # --- survivor (holds_empirically / inconclusive) ----------------------
            refined = (att.get("refined_statement") or "").strip()
            if action == "strengthen_and_retry" and refined and refined != current:
                current = refined
                self._emit("retry", depth=depth + 2, max=depth_cap, statement=current)
                continue
            # AMBICIÓN: en un superviviente de problema ABIERTO (holds_empirically) NO
            # paramos — hacemos la segunda jugada: intentar prueba y, si no cierra, buscar
            # una contribución PARCIAL demostrable (Feynman/Gödel/Euclides). Solo si hay un
            # motor real (explorer o proveedor); si no, escalamos honestamente.
            can_try = self._explorer is not None or self._can_llm()
            if (action == "attempt_proof" or v == "holds_empirically") and can_try:
                self._emit("proving", depth=depth + 1, max=depth_cap, statement=current)
                proof = self._attempt_proof(current, att.get("observation") or "")
                trail.append(proof)
                disp = proof.get("disposition")
                if disp == "verified":
                    disposition, final_verdict = "verified", "verified"
                    break
                if disp == "formally_supported":
                    # a core lemma is formally proved; the reduction bridge awaits a human
                    disposition = "formally_supported"
                    final_verdict = "formally_supported"
                    sketch = proof.get("sketch", "")
                    formal_support = proof.get("formal")
                    lemma = proof.get("lemma")
                    break
                sketch = proof.get("sketch", "") or sketch
                if v == "holds_empirically":
                    # open survivor, no full/bridge proof → seek an honest partial win
                    self._emit("contribution", depth=depth + 1, max=depth_cap,
                               statement=current)
                    contrib = self._seek_contribution(current)
                    if contrib:
                        contributions.append(contrib)
                        trail.append({"depth": "contribution", **contrib})
                    if not sketch:
                        sketch = self._sketch(current)
                    disposition = ("partial_progress"
                                   if any(c.get("proved") for c in contributions)
                                   else "needs_human_review")
                else:
                    disposition = "needs_human_review"
                break
            # escalate_to_human / drop (inconclusive with no proof move)
            disposition = ("needs_human_review" if v == "holds_empirically" else "dropped")
            if disposition == "needs_human_review":
                sketch = self._sketch(current)
            break
        result = {
            "original": statement, "final_statement": current,
            "disposition": disposition, "final_verdict": final_verdict,
            "sketch": sketch or None, "lemma": lemma,
            "formal_support": formal_support, "contributions": contributions,
            "trail": trail,
        }
        self._record(statement, result)
        return result

    def _verify_formal_or_z3(self, out: dict[str, Any]) -> dict[str, Any] | None:
        """Verify whichever engine the LLM filled: sympy (formal_claim) or Z3 (z3_claim).
        Returns the best pack {backend, claim, formal} (a 'proved' wins), or None."""
        best: dict[str, Any] | None = None
        # --- Euclides (sympy): algebra / analysis --------------------------------
        fc = {k: v for k, v in (out.get("formal_claim") or {}).items()
              if isinstance(v, str) and v.strip()}
        if fc.get("kind"):
            from .formal_verify import verify
            res = verify(str(fc["kind"]), **{k: v for k, v in fc.items() if k != "kind"})
            pack = {"backend": "sympy", "claim": fc, "formal": res}
            if res.get("result") == "proved":
                return pack
            best = pack
        # --- Gödel (Z3/SMT): logic / counting / quantified over ints·booleans -----
        zc_raw = out.get("z3_claim") or {}
        zc: dict[str, Any] = {}
        for k in ("kind", "expr", "sort"):
            v = zc_raw.get(k)
            if isinstance(v, str) and v.strip():
                zc[k] = v
        for k in ("vars", "assume"):
            v = zc_raw.get(k)
            if isinstance(v, list):
                zc[k] = [x for x in v if isinstance(x, str) and x.strip()]
        if zc.get("kind") and zc.get("expr"):
            from .proof_assistant import prove
            zres = prove(str(zc["kind"]), expr=zc.get("expr"), vars=zc.get("vars"),
                         assume=zc.get("assume"), sort=zc.get("sort"))
            pack = {"backend": "z3", "claim": zc, "formal": zres}
            if zres.get("result") == "proved":
                return pack
            if best is None:
                best = pack
        return best

    def _formalize_and_verify(self, statement: str, sketch: str) -> dict[str, Any] | None:
        """Reduce the human sketch to a symbolic LEMMA and try to PROVE it (sympy/Z3).

        Honesty: proving the lemma supports the argument; it does NOT machine-prove the
        reduction bridge. So a success yields `formally_supported`, never full `verified`.
        """
        prov = self._provider
        if prov is None:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return None
        try:
            out = prov.complete_json(
                f"{_FORMALIZE_SYS}\n\nAFIRMACIÓN: {statement}\nBOCETO/REDUCCIÓN: {sketch[:900]}",
                FORMALIZE_SCHEMA, temperature=0.2)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(out, dict):
            return None
        pack = self._verify_formal_or_z3(out)
        if pack is None:
            return None
        return {"lemma": out.get("lemma"), "reduction": out.get("reduction"), **pack}

    def _seek_contribution(self, statement: str) -> dict[str, Any] | None:
        """AMBITION: the open-problem survivor wasn't fully proved. Ask for a PARTIAL,
        VERIFIABLE contribution (necessary condition / bound / variant) and verify it
        mechanically. Honest: a proved contribution is real partial progress, NOT a
        solution to the open problem."""
        prov = self._provider
        if prov is None:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return None
        try:
            out = prov.complete_json(f"{_CONTRIB_SYS}\n\nCONJETURA: {statement}",
                                     CONTRIB_SCHEMA, temperature=0.3)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(out, dict):
            return None
        kind = str(out.get("kind") or "").strip()
        if kind in ("", "none"):
            return None
        pack = self._verify_formal_or_z3(out)
        proved = bool(pack and (pack.get("formal") or {}).get("result") == "proved")
        return {"kind": kind, "statement": out.get("statement") or "",
                "why_partial": out.get("why_partial") or "", "proved": proved,
                "backend": (pack or {}).get("backend"),
                "formal": (pack or {}).get("formal"),
                "claim": (pack or {}).get("claim")}

    def _attempt_proof(self, statement: str, sketch_hint: str = "") -> dict[str, Any]:
        """Try to prove a survivor: (1) direct formal proof of the whole statement via the
        explorer; (2) else reduce the sketch to a lemma and verify it symbolically; (3) else
        escalate with an honest proof sketch."""
        sketch = sketch_hint
        if self._explorer is not None:
            try:
                r = self._explorer.explore(statement, approaches=3, rounds=1)
                if r.get("verdict") == "verified":
                    return {"depth": "proof", "type": "formal_full",
                            "disposition": "verified", "detail": r.get("verdict_detail")}
                sketch = sketch or (r.get("why") or "")
            except Exception:  # noqa: BLE001
                pass
        if not sketch:
            sketch = self._sketch(statement)
        # (2) reduce the sketch to a verifiable core lemma
        fv = self._formalize_and_verify(statement, sketch)
        if fv and (fv.get("formal") or {}).get("result") == "proved":
            return {"depth": "proof", "type": "reduction",
                    "disposition": "formally_supported", "backend": fv.get("backend"),
                    "lemma": fv.get("lemma"), "reduction": fv.get("reduction"),
                    "formal": fv.get("formal"), "sketch": sketch}
        return {"depth": "proof", "type": "sketch",
                "disposition": "needs_human_review", "sketch": sketch}
