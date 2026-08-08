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


def run_council(project_id: str, claim: str, *, sf: Any = None, loop: Any = None,
                hypothesis_id: str | None = None, novelty: Any = None) -> dict[str, Any]:
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
                store.put(project_id, "literature", new_id("lit"),
                          {"title": t[:200], "year": h.get("year"), "doi": h.get("doi"),
                           "source": h.get("source"), "why": h.get("why"),
                           "origin": "consejo"},
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
    _live(project_id, {"persona": "bohr", "from_persona": "godel", "next_persona": "gauss",
                       "label": f"Ciclo terminado: {disp}", "pct": 100, "will_retry": "no",
                       "seq": seq["n"] + 2, "hypothesis_id": hid, "round": 1,
                       "max_rounds": 3, "statement": final_stmt[:160],
                       "disposition": disp, "done": True,
                       "summary": {"reformulations": len(seen) - 1,
                                   "lemmas_proved": n_lem,
                                   "novelty": nv_verdict, "dossier": made_dossier}}, sf=sf)
    return {"hypothesis_id": hid, "disposition": disp, "final_verdict": final_v,
            "final_statement": final_stmt,
            "n_reformulations": len(seen) - 1,
            "contributions": res.get("contributions") or [],
            "lemma": res.get("lemma"),
            "novelty": nv_verdict, "dossier": made_dossier}
