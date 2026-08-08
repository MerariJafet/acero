"""Puente investigador → ledger del proyecto.

Cierra la brecha #1: hasta ahora los motores matemáticos (Explorer, Probe, Gödel,
ResearchLoop) corrían AL LADO del dashboard. Este puente los conecta AL proyecto: al
atacar un claim se escriben una **hipótesis** (kind='candidate') y un **experimento**
(kind='experiment' con su veredicto) en el mismo ledger que lee el dashboard. Así los
KPIs, las fichas de cada personaje y las pelotas del Consejo se actualizan solos —
el trabajo del Consejo ES el trabajo de investigación, un solo flujo.

Honestidad: el veredicto se guarda tal cual lo dio el probador (verified / refuted /
holds_empirically / formally_supported / inconclusive); nada se infla.
"""

from __future__ import annotations

from typing import Any

from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

# qué personaje "firma" cada tipo de trabajo (para la procedencia en el ledger)
PERSONA_ACTOR = {
    "hilbert": "Hilbert", "euler": "Euler", "hipatia": "Hipatia",
    "arquimedes": "Arquímedes", "davinci": "Da Vinci", "kepler": "Kepler",
    "tycho": "Tycho", "popper": "Popper", "euclides": "Euclides", "godel": "Gödel",
    "aristoteles": "Aristóteles", "feynman": "Feynman", "bohr": "Bohr", "gauss": "Gauss",
}


def _store(sf: Any = None) -> DiscoveryStore:
    sf = sf or default_session_factory()
    return DiscoveryStore(sf, ResearchLedger(sf))


def record_hypothesis(project_id: str, claim: str, *, persona: str = "hilbert",
                      sf: Any = None) -> str:
    """Register a hypothesis (kind='candidate') so the dashboard counts it.

    Writes `tag` (H1, H2… by arrival order) and `title` because the phase cards render
    exactly those fields — without them the card shows an empty 'H?:'.

    DEDUP: si ya existe una hipótesis VIVA con la MISMA conjetura (relanzar el ciclo de
    Bohr sobre el mismo tema), se REUTILIZA — los nuevos experimentos se cuelgan de ella
    en vez de crear H1..Hn idénticas."""
    store = _store(sf)
    norm = " ".join(claim.split()).lower()
    for r in store.list_rows(project_id):
        if r.get("kind") != "candidate":
            continue
        if str(r.get("status") or "").upper() in ("REJECTED", "CLOSED", "ARCHIVED"):
            continue
        pay = r.get("payload") or {}
        prev = " ".join(str(pay.get("claim") or pay.get("statement") or "").split()).lower()
        if prev and prev == norm:
            return str(r["id"])
    hid = new_id("hyp")
    n = len(store.list_objects(project_id, kind="candidate")) + 1
    store.put(project_id, "candidate", hid,
              {"id": hid, "claim": claim, "statement": claim, "title": claim[:140],
               "description": claim, "tag": f"H{n}", "origin": "consejo", "by": persona},
              status="PROPOSED", actor=PERSONA_ACTOR.get(persona, persona),
              summary=claim[:120])
    return hid


# --- estado EN VIVO del ciclo del Consejo (la barra superior lo lee) -----------
# Un solo objeto por proyecto (kind='council_status') que se sobreescribe en cada
# etapa: quién trabaja ahora, de dónde viene, a dónde pasará, ronda, ¿otra vuelta?,
# y % de avance del ciclo. El dashboard lo consulta en polling.
def _live(project_id: str, payload: dict[str, Any], *, sf: Any = None) -> None:
    try:
        store = _store(sf)
        store.put(project_id, "council_status", f"cstat_{project_id}",
                  {**payload, "seq": int(payload.get("seq") or 0)},
                  status=("DONE" if payload.get("done") else "LIVE"), actor="Bohr",
                  summary=str(payload.get("label") or "")[:120])
    except Exception:  # noqa: BLE001 - el estado en vivo nunca rompe el ciclo
        pass


# evento del ResearchLoop → etapa visible (persona verde, de-dónde amarillo,
# a-dónde naranja, % del ciclo)
_STAGE = {
    "probing":      {"persona": "popper", "from_persona": "hilbert", "next_persona": "feynman",
                     "label": "Popper busca contraejemplos", "pct": 30, "will_retry": "decidiendo"},
    "deciding":     {"persona": "feynman", "from_persona": "popper", "next_persona": "godel",
                     "label": "Feynman decide la segunda jugada", "pct": 50, "will_retry": "decidiendo"},
    "retry":        {"persona": "feynman", "from_persona": "popper", "next_persona": "popper",
                     "label": "Reformulada — dará OTRA VUELTA", "pct": 55, "will_retry": "sí"},
    "proving":      {"persona": "godel", "from_persona": "feynman", "next_persona": "aristoteles",
                     "label": "Gödel/Euclides intentan demostrar", "pct": 72, "will_retry": "no"},
    "contribution": {"persona": "godel", "from_persona": "feynman", "next_persona": "gauss",
                     "label": "Buscando contribución parcial demostrable", "pct": 85, "will_retry": "no"},
}


def record_result(project_id: str, claim: str, result: dict[str, Any], *,
                  persona: str = "popper", hypothesis_id: str | None = None,
                  sf: Any = None) -> dict[str, Any]:
    """Write the outcome of an attack as an experiment (with its verdict) + hypothesis.

    `result` is what MathProbe/MathExplorer/ResearchLoop returns; we keep the verdict
    verbatim. Returns the created ids so the caller can link/refresh the view.
    """
    store = _store(sf)
    hid = hypothesis_id or record_hypothesis(project_id, claim, persona=persona, sf=sf)
    verdict = str(result.get("verdict") or result.get("disposition") or "inconclusive")
    comp = result.get("computational") or {}
    eid = new_id("exp")
    store.put(project_id, "experiment", eid, {
        "claim": claim, "method": PERSONA_ACTOR.get(persona, persona),
        "parent": hid, "origin": "consejo",
        "result": {"verdict": verdict, "detail": result.get("detail")
                   or result.get("verdict_detail") or "",
                   "counterexample": comp.get("counterexample")
                   or result.get("counterexample"),
                   "n_tested": comp.get("n_tested")},
        "approaches": result.get("viable_approaches") or [],
        "sketch": result.get("sketch"), "novelty": result.get("novelty"),
    }, status="RUN", parent_id=hid,
        actor=PERSONA_ACTOR.get(persona, persona), summary=f"{persona}: {verdict}")
    # a concrete refutation is a negative result the dashboard can surface
    if verdict == "refuted":
        store.put(project_id, "negative", new_id("neg"),
                  {"claim": claim, "counterexample": comp.get("counterexample")},
                  status="CONFIRMED", parent_id=hid, actor=PERSONA_ACTOR.get(persona, persona),
                  summary=f"contraejemplo a: {claim[:80]}")
    return {"hypothesis_id": hid, "experiment_id": eid, "verdict": verdict}


def record_reformulation(project_id: str, statement: str, *, angle: str = "",
                         parent_id: str | None = None, sf: Any = None) -> str:
    """Feynman's 'second move': a sharpened/alternative statement (kind='reformulation')."""
    store = _store(sf)
    rid = new_id("ref")
    store.put(project_id, "reformulation", rid,
              {"statement": statement, "angle": angle, "origin": "consejo"},
              status="PROPOSED", parent_id=parent_id, actor="Feynman",
              summary=statement[:120])
    return rid


def record_lemma(project_id: str, statement: str, *, proved: bool = False, backend: str = "",
                 detail: str = "", kind: str = "", parent_id: str | None = None,
                 sf: Any = None) -> str:
    """Gödel/Euclides' verifiable partial result (kind='lemma'): a proved lemma, a
    necessary condition on any counterexample, a bound, or a weaker variant. Honest:
    `proved` reflects the mechanical verification, and a proved contribution is partial
    progress, NEVER a solution to an open problem."""
    store = _store(sf)
    lid = new_id("lem")
    store.put(project_id, "lemma", lid,
              {"statement": statement, "proved": bool(proved), "backend": backend,
               "detail": detail, "contribution_kind": kind, "origin": "consejo"},
              status=("PROVED" if proved else "PROPOSED"), parent_id=parent_id,
              actor="Gödel", summary=statement[:120])
    return lid


def record_decision(project_id: str, to_persona: str, reason: str, *,
                    parent_id: str | None = None, sf: Any = None) -> str:
    """Bohr ORQUESTA: cada pase de estafeta queda registrado con su PORQUÉ
    (kind='decision'). Así el Consejo muestra quién decidió qué y por qué —
    el papel de director, no solo de arrancador."""
    store = _store(sf)
    did = new_id("dec")
    store.put(project_id, "decision", did,
              {"to": to_persona, "reason": reason, "origin": "consejo"},
              status="TAKEN", parent_id=parent_id, actor="Bohr",
              summary=f"Bohr → {to_persona}: {reason[:90]}")
    return did


# el PORQUÉ de cada asignación de Bohr (determinista, derivado del estado real)
_DECISION_WHY = {
    "probing": "sin contraejemplo no hay ciencia: Popper ataca computacionalmente",
    "deciding": "interpretar el veredicto y elegir la segunda jugada",
    "retry": "enunciado reformulado → vuelve a Popper con la versión afinada",
    "proving": "sobrevivió a la búsqueda: Gödel/Euclides intentan demostrarlo",
    "contribution": "la prueba completa no cerró: buscar contribución parcial demostrable",
}


def _bohr_report(claim: str, final_stmt: str, disp: str, final_v: Any, nv_verdict: str,
                 n_ref: int, n_lem: int, res: dict[str, Any], made_dossier: bool,
                 crit_verdict: str, n_anom: int = 0,
                 papers: list[dict[str, Any]] | None = None) -> str:
    """La BITÁCORA de Bohr: un informe tipo paper del ciclo — qué hizo, cómo, con qué
    iteraciones, qué encontró, y si merece camino a publicación o queda DOCUMENTADO para
    estudio humano. Determinista: cada línea sale de evidencia del ledger, no de prosa
    inventada."""
    rounds_all = [t for t in (res.get("trail") or []) if isinstance(t.get("depth"), int)]
    n_cases = max((int(t.get("n_tested") or 0) for t in rounds_all), default=0)
    resumen = {
        "verified": "La conjetura quedó DEMOSTRADA formalmente. Pasa a revisión humana "
                    "para confirmar la demostración.",
        "refuted": "La conjetura es FALSA: existe un contraejemplo concreto y robusto. "
                   "Eso también es conocimiento — dice exactamente dónde falla la idea.",
        "partial_progress": f"No demostramos toda la conjetura, pero SÍ probamos "
                            f"mecánicamente un pedazo (lema/cota/condición). Sobrevivió "
                            f"a {n_cases:,} casos. Progreso real, no la meta.",
        "formally_supported": "Se probó el LEMA NÚCLEO del argumento; falta que un "
                              "humano revise el puente completo de la demostración.",
        "needs_human_review": f"La conjetura SOBREVIVIÓ: tras {n_ref} reformulación(es) "
                              f"y {n_cases:,} casos sin contraejemplo real, no pudimos "
                              f"ni demostrarla ni refutarla. Hay un boceto de por dónde "
                              f"demostrarla — la decisión pasa a ti.",
        "inconclusive": "El ciclo no logró concluir nada: ni contraejemplo ni "
                        "verificación suficiente. Recomiendo afinar la conjetura.",
        "dropped": "La conjetura se descartó por poco fértil o mal planteada.",
    }.get(disp, disp)
    L: list[str] = []
    L.append(f"# Informe del Consejo — dirigido por Bohr\n")
    L.append(f"## 0. Resumen ejecutivo (en cristiano)\n{resumen}\n")
    L.append(f"## 1. Conjetura investigada\n{claim}\n")
    if final_stmt and final_stmt != claim:
        L.append(f"Enunciado FINAL tras reformulaciones: {final_stmt}\n")
    L.append(f"## 2. Novedad (Hipatia)\n"
             + {"already_resolved": "YA RESUELTA en la literatura — el valor aquí es "
                                    "reproducir/estudiar, no descubrir.",
                "likely_open": "Probablemente ABIERTA: no se halló un resolver directo.",
                "uncertain": "Incierta: papers relacionados sin resolver directo.",
                "": "No evaluada en este ciclo."}.get(nv_verdict, nv_verdict) + "\n")
    L.append("## 3. Ataque computacional (Popper) — iteraciones")
    rounds = [t for t in (res.get("trail") or []) if isinstance(t.get("depth"), int)]
    if rounds:
        for t in rounds:
            L.append(f"- Ronda {t['depth']}: veredicto **{t.get('verdict')}**"
                     + (f" · {t.get('n_tested')} casos" if t.get("n_tested") else "")
                     + (f" · contraejemplo: {t.get('counterexample')}"
                        if t.get("counterexample") else "")
                     + (f"\n  - Observación (Feynman): {str(t.get('observation'))[:220]}"
                        if t.get("observation") else "")
                     + (f"\n  - Jugada elegida: {t.get('next_action')}"
                        if t.get("next_action") else ""))
    else:
        L.append("- (sin rondas registradas)")
    L.append(f"\n## 4. Segunda jugada (Feynman)\nReformulaciones: {n_ref}\n")
    L.append("## 5. Demostración (Gödel/Euclides)")
    if res.get("lemma"):
        L.append(f"- Lema núcleo: {res['lemma']}")
    for c in res.get("contributions") or []:
        L.append(f"- Contribución [{c.get('kind')}] "
                 + ("**PROBADA** " if c.get("proved") else "propuesta ")
                 + f"({c.get('backend') or 's/m'}): {str(c.get('statement'))[:200]}"
                 + (f"\n  - Por qué es parcial: {str(c.get('why_partial'))[:200]}"
                    if c.get("why_partial") else ""))
    if not res.get("lemma") and not (res.get("contributions") or []):
        L.append("- Nada demostrable en este ciclo.")
    L.append(f"\n## 6. Crítica (Aristóteles)\n"
             + (f"Veredicto del crítico: **{crit_verdict}** (ver su ficha con objeciones)."
                if crit_verdict else "No emitida en este ciclo."))
    L.append(f"\n## 6b. Anomalías (Kepler)\n"
             + (f"{n_anom} hipótesis NUEVA(s) cosechada(s) de discrepancias medidas "
                "(marcadas 🔥 en el tablero de hipótesis)."
                if n_anom else "Sin discrepancias medidas que cosechar en este ciclo."))
    L.append(f"\n## 7. Disposición final\n**{disp}**"
             + (f" (veredicto computacional: {final_v})" if final_v else ""))
    if res.get("sketch"):
        L.append(f"\nBoceto de demostración (honesto, incompleto):\n> "
                 f"{str(res['sketch'])[:500]}")
    mature = disp in ("verified", "formally_supported", "partial_progress")
    L.append("\n## 8. ¿Publicación o estudio?")
    if mature:
        L.append("HAY RESULTADO MADURO → dossier "
                 + ("EMPAQUETADO" if made_dossier else "pendiente")
                 + " rumbo a revisión humana. Siguiente: Misión completa (evidencia con "
                   "datos/literatura) y attestation externa. NADA se publica sin humano.")
    else:
        L.append("SIN resultado maduro — este intento queda DOCUMENTADO para estudio "
                 "humano (los caminos que no cierran también son conocimiento).")
    L.append("\n## Referencias — lecturas de Hipatia (de dónde salió la información)")
    if papers:
        for h in papers[:15]:
            t = str((h or {}).get("title") or "").strip()
            if not t:
                continue
            src = str(h.get("source") or "fuente")
            yr = f" ({h.get('year')})" if h.get("year") else ""
            doi = f" · doi:{h.get('doi')}" if h.get("doi") else ""
            why = f"\n  - por qué importa: {str(h.get('why'))[:160]}" if h.get("why") else ""
            L.append(f"- [{src}] {t[:150]}{yr}{doi}{why}")
        if len(papers) > 15:
            L.append(f"- …y {len(papers) - 15} lecturas más en la ficha de Hipatia.")
    else:
        L.append("- Sin lecturas registradas en este ciclo (revisa la ficha de Hipatia).")
    L.append("\n## 9. Recomendación de Bohr (siguiente herramienta)")
    L.append({"refuted": "- El contraejemplo es información: 🔥 Cazar anomalías o "
                         "reformular con el destilador del chat.",
              "inconclusive": "- Afinar la conjetura (destilador 🔬), 🧭 preguntas EVA, "
                              "🌊 barrido masivo de variantes, o activar el 🔁 Loop "
                              "autónomo (PI) para que itere solo.",
              "needs_human_review": "- Revisar el boceto; correr 🚀 Misión completa "
                                    "(literatura + experimentos con datos reales).",
              }.get(disp, "- 🚀 Misión completa para evidencia independiente y luego "
                          "📤 paquete verificable + attestation externa."))
    L.append("\n## 10. ¿Qué tan cerca estamos de la FRONTERA del conocimiento?")
    if nv_verdict == "already_resolved":
        L.append("DETRÁS de la frontera: esto ya está resuelto en la literatura. No es "
                 "derrota — es el mapa: el valor de este ciclo es APRENDER el resultado, "
                 "reproducirlo con rigor y usarlo como escalón hacia una variante que "
                 "SÍ esté abierta.")
    elif disp in ("verified", "partial_progress", "formally_supported"):
        L.append("TOCANDO la frontera: hay un pedazo demostrado mecánicamente sobre una "
                 "pregunta sin resolver directo. Si la revisión humana confirma novedad "
                 "y validez, esto sería conocimiento NUEVO — todavía no lo es.")
    elif nv_verdict == "likely_open":
        L.append("EN la frontera: la pregunta es probablemente ABIERTA (nadie la "
                 "resolvió directo). Sobrevivir búsquedas nos pone en el borde; cruzar "
                 "al conocimiento nuevo exige demostración o evidencia decisiva, y "
                 "siempre, validación humana.")
    else:
        L.append("EN CAMINO a la frontera: aún clasificando si la pregunta es nueva o "
                 "ya resuelta. El siguiente ciclo (con la lectura de Hipatia) lo dirá.")
    L.append("\n---\n*Techo epistémico: nada de lo anterior es un descubrimiento hasta "
             "que lo valide revisión científica humana.*")
    return "\n".join(L)


_NARRATOR_SYS = (
    "Eres BOHR, director del Consejo de ACERO. Escribe el INFORME NARRATIVO del ciclo "
    "para tu colega humano (español claro, 400-700 palabras, tono de paper de divulgación "
    "interna). REGLAS DE HONESTIDAD ABSOLUTAS: usa SOLO los hechos del apéndice que te "
    "doy; si un dato no aparece, NO lo inventes; jamás digas que algo quedó demostrado o "
    "descubierto salvo que el apéndice lo diga textualmente; explica cada término técnico "
    "en lenguaje llano la primera vez (p.ej. 'refuted = encontramos un caso concreto "
    "donde falla'). Estructura con encabezados: 1) Qué nos preguntamos y por qué importa; "
    "2) Qué hicimos, paso a paso (nombra qué personaje hizo qué y POR QUÉ se decidió "
    "así); 3) Qué encontramos (con los números); 4) Qué significa — y qué NO significa; "
    "5) Qué sigue y qué decisión te toca a ti como humano.")


def run_council(project_id: str, claim: str, *, sf: Any = None, loop: Any = None,
                hypothesis_id: str | None = None, novelty: Any = None,
                critic: Any = None, anomalies: Any = None,
                narrator: Any = None) -> dict[str, Any]:
    """Bohr dirige el ciclo AMBICIOSO sobre `claim` y registra el trabajo por personaje:
    Hilbert (hipótesis), Popper (resultado empírico/veredicto), Feynman (reformulaciones),
    Gödel/Euclides (lemas y contribuciones parciales verificadas). Un solo flujo → el
    dashboard y las fichas del Consejo se actualizan solos. Nada se infla: el veredicto y
    el estado 'partial_progress' salen tal cual del ResearchLoop."""
    from ..science.research_loop import ResearchLoop
    hid = hypothesis_id or record_hypothesis(project_id, claim, persona="hilbert", sf=sf)
    seq = {"n": 0}

    def _on_event(ev: dict[str, Any]) -> None:
        name = str(ev.get("event") or "")
        st = _STAGE.get(name)
        if not st:
            return
        seq["n"] += 1
        _live(project_id, {**st, "seq": seq["n"], "hypothesis_id": hid,
                           "round": int(ev.get("depth") or 1),
                           "max_rounds": int(ev.get("max") or 3),
                           "statement": str(ev.get("statement") or claim)[:160],
                           "done": False}, sf=sf)
        # Bohr deja constancia de a quién asigna y POR QUÉ (su papel de director)
        why = _DECISION_WHY.get(name)
        if why:
            extra = f" (ronda {ev.get('depth')})" if ev.get("depth") else ""
            v = f" — veredicto: {ev.get('verdict')}" if ev.get("verdict") else ""
            record_decision(project_id, st["persona"], f"{why}{v}{extra}",
                            parent_id=hid, sf=sf)

    _live(project_id, {"persona": "hilbert", "from_persona": "bohr",
                       "next_persona": "hipatia", "label": "Hilbert registró la conjetura",
                       "pct": 5, "will_retry": "decidiendo", "seq": 0, "round": 1,
                       "max_rounds": 3, "hypothesis_id": hid,
                       "statement": claim[:160], "done": False}, sf=sf)

    # --- HIPATIA PRIMERO: ¿ya está resuelta? — literatura REAL al ledger -----------
    # (inyectable en tests; en modo full-auto usa el NoveltyChecker multi-fuente)
    store = _store(sf)
    nv_verdict = ""
    papers_used: list[dict[str, Any]] = []      # lecturas de Hipatia → referencias
    checker = novelty
    if checker is None and loop is None:
        def checker(c: str) -> dict[str, Any]:
            from ..discovery.novelty_check import NoveltyChecker
            return NoveltyChecker().check(c)
    if checker is not None:
        _live(project_id, {"persona": "hipatia", "from_persona": "hilbert",
                           "next_persona": "popper",
                           "label": "Hipatia busca en la literatura (¿ya se hizo?)",
                           "pct": 15, "will_retry": "decidiendo", "seq": 0, "round": 1,
                           "max_rounds": 3, "hypothesis_id": hid,
                           "statement": claim[:160], "done": False}, sf=sf)
        record_decision(project_id, "hipatia",
                        "antes de gastar cómputo, verificar si la conjetura ya está "
                        "resuelta en la literatura (anti-Erdősgate)",
                        parent_id=hid, sf=sf)
        try:
            nv = checker(claim) or {}
            nv_verdict = str(nv.get("verdict") or "")
            seen_titles: set[str] = set()
            for h in (nv.get("resolving_papers") or []) + (nv.get("hits") or [])[:6]:
                t = str((h or {}).get("title") or "").strip()
                if not t or t.lower() in seen_titles:
                    continue
                seen_titles.add(t.lower())
                paper = {"title": t[:200], "year": h.get("year"), "doi": h.get("doi"),
                         "source": h.get("source"), "why": h.get("why"),
                         "origin": "consejo"}
                papers_used.append(paper)
                store.put(project_id, "literature", new_id("lit"), paper,
                          status="FOUND", parent_id=hid, actor="Hipatia",
                          summary=f"Hipatia: {t[:90]}")
            # la tarjeta de la hipótesis muestra el chip de novedad
            store.update_payload(hid, {"novelty": {
                "status": {"already_resolved": "asentada",
                           "likely_open": "abierta"}.get(nv_verdict, "sin_evaluar"),
                "known": str(nv.get("rationale") or "")[:400], "gap": "",
                "discovery_path": str(nv.get("recommendation") or "")[:300]}})
        except Exception:  # noqa: BLE001 - Hipatia caída no detiene el ciclo
            pass

    lp = loop or ResearchLoop(on_event=_on_event)
    res = lp.investigate(claim)
    disp = str(res.get("disposition") or "inconclusive")
    final_v = res.get("final_verdict")
    final_stmt = res.get("final_statement") or claim
    # Popper: el resultado empírico / veredicto principal (con su cota de búsqueda)
    record_result(project_id, final_stmt,
                  {"verdict": final_v or disp, "detail": res.get("sketch") or "",
                   "disposition": disp}, persona="popper", hypothesis_id=hid, sf=sf)
    # Feynman: reformulaciones (pasos del trail que cambiaron el enunciado)
    seen = {claim.strip()}
    for t in res.get("trail") or []:
        st = str(t.get("statement") or "").strip()
        if st and st not in seen and t.get("observation") is not None:
            record_reformulation(project_id, st, angle=str(t.get("observation") or "")[:80],
                                  parent_id=hid, sf=sf)
            seen.add(st)
    # Gödel/Euclides: lema formalmente apoyado (si lo hubo)
    if res.get("lemma"):
        record_lemma(project_id, str(res["lemma"]),
                     proved=disp in ("formally_supported", "verified"),
                     detail="lema núcleo de la reducción", parent_id=hid, sf=sf)
    # Gödel/Euclides: contribuciones parciales verificadas (condición necesaria/cota/variante)
    for c in res.get("contributions") or []:
        record_lemma(project_id, str(c.get("statement") or ""), proved=bool(c.get("proved")),
                     backend=str(c.get("backend") or ""), detail=str(c.get("why_partial") or ""),
                     kind=str(c.get("kind") or ""), parent_id=hid, sf=sf)
    n_lem = (sum(1 for c in (res.get("contributions") or []) if c.get("proved"))
             + (1 if res.get("lemma") and disp in ("formally_supported", "verified") else 0))

    # --- ARISTÓTELES AUTOMÁTICO: la crítica ya no se pide a mano -------------------
    crit_verdict = ""
    critic_fn = critic
    if critic_fn is None and loop is None:
        def critic_fn(pid_: str, hid_: str, ctx_: str) -> dict[str, Any]:
            from .critic import CriticAgent
            return CriticAgent().critique_now(pid_, hid_, "hipotesis", ctx_, use_ai=True)
    if critic_fn is not None:
        _live(project_id, {"persona": "aristoteles", "from_persona": "godel",
                           "next_persona": "gauss",
                           "label": "Aristóteles critica el resultado (revisor hostil)",
                           "pct": 90, "will_retry": "no", "seq": seq["n"] + 1,
                           "round": 1, "max_rounds": 3, "hypothesis_id": hid,
                           "statement": final_stmt[:160], "done": False}, sf=sf)
        record_decision(project_id, "aristoteles",
                        "nada avanza sin pasar por el revisor hostil: criticar el "
                        "resultado ANTES de decidir publicación", parent_id=hid, sf=sf)
        try:
            ctx = (f"Conjetura: {final_stmt}\n"
                   f"Novedad (Hipatia): {nv_verdict or 'no evaluada'}\n"
                   f"Veredicto computacional: {final_v or disp}\n"
                   f"Reformulaciones: {len(seen) - 1} · Lemas probados: {n_lem}\n"
                   f"Disposición del ciclo: {disp}\n"
                   f"Boceto: {str(res.get('sketch') or '')[:400]}")
            crit = critic_fn(project_id, hid, ctx) or {}
            crit_verdict = str(crit.get("verdict") or "")
        except Exception:  # noqa: BLE001 - crítico caído no detiene el cierre
            pass

    # --- KEPLER: cosechar ANOMALÍAS → hipótesis NUEVAS (como con los datos de Tycho) --
    n_anom = 0
    anom_fn = anomalies
    if anom_fn is None and loop is None:
        def anom_fn(pid_: str) -> dict[str, Any]:
            from .anomalies import AnomalyEngine
            return AnomalyEngine().harvest(pid_)
    if anom_fn is not None:
        _live(project_id, {"persona": "kepler", "from_persona": "aristoteles",
                           "next_persona": "gauss",
                           "label": "Kepler cosecha anomalías → hipótesis nuevas",
                           "pct": 93, "will_retry": "no", "seq": seq["n"] + 1,
                           "round": 1, "max_rounds": 3, "hypothesis_id": hid,
                           "statement": final_stmt[:160], "done": False}, sf=sf)
        record_decision(project_id, "kepler",
                        "como Kepler con los datos de Tycho: toda discrepancia medida "
                        "es semilla de una hipótesis nueva", parent_id=hid, sf=sf)
        try:
            av = anom_fn(project_id) or {}
            n_anom = len(av.get("created") or [])
        except Exception:  # noqa: BLE001 - sin anomalías no se detiene el cierre
            pass

    # --- GAUSS AL FINAL: solo lo MADURO se empaqueta (dossier → revisión humana) ----
    made_dossier = False
    if disp in ("verified", "formally_supported", "partial_progress"):
        _live(project_id, {"persona": "gauss", "from_persona": "godel",
                           "next_persona": "gauss",
                           "label": "Gauss empaqueta el dossier (pauca sed matura)",
                           "pct": 95, "will_retry": "no", "seq": seq["n"] + 1,
                           "round": 1, "max_rounds": 3, "hypothesis_id": hid,
                           "statement": final_stmt[:160], "done": False}, sf=sf)
        record_decision(project_id, "gauss",
                        f"resultado maduro ({disp}): empaquetar dossier para revisión "
                        "humana — pauca sed matura", parent_id=hid, sf=sf)
        try:
            from .workspace import WorkspaceService
            WorkspaceService(sf).dossier(project_id, final_stmt)
            made_dossier = True
        except Exception:  # noqa: BLE001 - el dossier fallido no borra el resultado
            pass
    else:
        record_decision(project_id, "revisión humana",
                        f"ciclo cerrado en '{disp}': no hay resultado maduro que "
                        "empaquetar — la decisión de la siguiente jugada es humana",
                        parent_id=hid, sf=sf)
    # --- BITÁCORA DE BOHR: informe tipo paper del ciclo, SIEMPRE (maduro o no) ------
    report_md = _bohr_report(claim, final_stmt, disp, final_v, nv_verdict,
                             len(seen) - 1, n_lem, res, made_dossier, crit_verdict,
                             n_anom=n_anom, papers=papers_used)
    # capa NARRATIVA: Bohr redacta la explicación en lenguaje humano a partir de los
    # HECHOS del apéndice (nunca inventa); si no hay proveedor, queda el determinista.
    narr = ""
    narrator_fn = narrator
    if narrator_fn is None and loop is None:
        def narrator_fn(facts: str) -> str:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider(timeout_sec=240)
            if prov is None or not prov.available():
                return ""
            return prov.complete(f"{_NARRATOR_SYS}\n\nHECHOS (apéndice del ledger):\n"
                                 f"{facts[:6000]}",
                                 temperature=0.4, max_tokens=1700).text.strip()
    if narrator_fn is not None:
        _live(project_id, {"persona": "bohr", "from_persona": "gauss",
                           "next_persona": "gauss",
                           "label": "Bohr redacta el informe narrativo",
                           "pct": 97, "will_retry": "no", "seq": seq["n"] + 1,
                           "round": 1, "max_rounds": 3, "hypothesis_id": hid,
                           "statement": final_stmt[:160], "done": False}, sf=sf)
        try:
            narr = str(narrator_fn(report_md) or "").strip()[:9000]
        except Exception:  # noqa: BLE001 - sin narrativa queda el informe determinista
            narr = ""
    full_md = (f"# Informe narrativo — Bohr\n\n{narr}\n\n---\n\n"
               f"# APÉNDICE — datos crudos del ledger\n\n{report_md}"
               if narr else report_md)
    store.put(project_id, "report", new_id("rep"),
              {"markdown": full_md, "disposition": disp,
               "claim": final_stmt[:200], "origin": "consejo"},
              status=("PUBLISHABLE_CANDIDATE" if made_dossier else "FOR_STUDY"),
              parent_id=hid, actor="Bohr",
              summary=f"informe del ciclo: {disp}")

    _live(project_id, {"persona": "bohr", "from_persona": "godel", "next_persona": "gauss",
                       "label": f"Ciclo terminado: {disp}", "pct": 100, "will_retry": "no",
                       "seq": seq["n"] + 2, "hypothesis_id": hid, "round": 1,
                       "max_rounds": 3, "statement": final_stmt[:160],
                       "disposition": disp, "done": True,
                       "summary": {"reformulations": len(seen) - 1,
                                   "lemmas_proved": n_lem, "critic": crit_verdict,
                                   "anomalies": n_anom,
                                   "novelty": nv_verdict, "dossier": made_dossier}}, sf=sf)
    return {"hypothesis_id": hid, "disposition": disp, "final_verdict": final_v,
            "final_statement": final_stmt,
            "n_reformulations": len(seen) - 1,
            "contributions": res.get("contributions") or [],
            "lemma": res.get("lemma"), "critic": crit_verdict, "anomalies": n_anom,
            "novelty": nv_verdict, "dossier": made_dossier, "report": True}


def regenerate_report(project_id: str, *, sf: Any = None,
                      narrator: Any = None) -> dict[str, Any]:
    """Reconstruye el informe de Bohr DESDE EL LEDGER (sin correr otro ciclo): útil
    cuando el motor del informe mejora (narrativa, referencias) y quieres el reporte
    nuevo del ciclo ya corrido. Honesto: solo usa lo que quedó registrado."""
    store = _store(sf)
    rows = store.list_rows(project_id)
    ulid = lambda r: str(r["id"]).split("_", 1)[-1]  # noqa: E731
    cands = sorted((r for r in rows if r["kind"] == "candidate"), key=ulid)
    if not cands:
        return {"ok": False, "error": "no hay hipótesis en el proyecto"}
    reports = sorted((r for r in rows if r["kind"] == "report"), key=ulid)
    hid = (reports[-1].get("parent_id") if reports else None) or cands[-1]["id"]
    cand = next((r for r in rows if r["id"] == hid), cands[-1])
    hid = cand["id"]
    pay = cand["payload"] or {}
    claim = str(pay.get("claim") or pay.get("statement") or pay.get("title") or "")
    kids = [r for r in rows if r.get("parent_id") == hid]
    exps = sorted((r for r in kids if r["kind"] == "experiment"), key=ulid)
    trail = []
    for i, e in enumerate(exps):
        r_ = (e["payload"] or {}).get("result") or {}
        trail.append({"depth": i + 1, "verdict": r_.get("verdict"),
                      "n_tested": r_.get("n_tested"),
                      "counterexample": r_.get("counterexample")})
    refs = [r for r in kids if r["kind"] == "reformulation"]
    lems = [r["payload"] or {} for r in kids if r["kind"] == "lemma"]
    contributions = [{"kind": (x.get("contribution_kind") or "lema"),
                      "statement": x.get("statement"), "proved": x.get("proved"),
                      "backend": x.get("backend"), "why_partial": x.get("detail")}
                     for x in lems]
    crits = sorted((r for r in rows if r["kind"] == "critique"), key=ulid)
    crit_verdict = str((crits[-1]["payload"] or {}).get("verdict") or "") if crits else ""
    papers = [r["payload"] or {} for r in rows if r["kind"] == "literature"]
    cs = next((r["payload"] for r in rows if r["kind"] == "council_status"), None) or {}
    disp = str(cs.get("disposition")
               or (reports[-1]["payload"].get("disposition") if reports else "")
               or "needs_human_review")
    nv_map = {"asentada": "already_resolved", "abierta": "likely_open"}
    nv_verdict = nv_map.get(str((pay.get("novelty") or {}).get("status") or ""), "")
    sketch = str((exps[-1]["payload"].get("result") or {}).get("detail") or "") if exps else ""
    res = {"trail": trail, "contributions": contributions, "lemma": None,
           "sketch": sketch[:600]}
    made_dossier = any(r["kind"] == "dossier" for r in rows)
    final_stmt = str(cs.get("statement") or claim)
    report_md = _bohr_report(claim, final_stmt, disp, cs.get("disposition"), nv_verdict,
                             len(refs), sum(1 for x in lems if x.get("proved")), res,
                             made_dossier, crit_verdict, n_anom=0, papers=papers)
    narr = ""
    narrator_fn = narrator
    if narrator_fn is None:
        def narrator_fn(facts: str) -> str:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider(timeout_sec=240)
            if prov is None or not prov.available():
                return ""
            return prov.complete(f"{_NARRATOR_SYS}\n\nHECHOS (apéndice del ledger):\n"
                                 f"{facts[:6000]}",
                                 temperature=0.4, max_tokens=1700).text.strip()
    try:
        narr = str(narrator_fn(report_md) or "").strip()[:9000]
    except Exception:  # noqa: BLE001
        narr = ""
    full_md = (f"# Informe narrativo — Bohr\n\n{narr}\n\n---\n\n"
               f"# APÉNDICE — datos crudos del ledger\n\n{report_md}"
               if narr else report_md)
    rid = new_id("rep")
    store.put(project_id, "report", rid,
              {"markdown": full_md, "disposition": disp, "claim": final_stmt[:200],
               "origin": "consejo-regenerado"},
              status=("PUBLISHABLE_CANDIDATE" if made_dossier else "FOR_STUDY"),
              parent_id=hid, actor="Bohr",
              summary=f"informe regenerado: {disp}")
    return {"ok": True, "report_id": rid, "disposition": disp,
            "n_papers": len(papers), "narrative": bool(narr)}
