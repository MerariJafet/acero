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
    """Register a hypothesis (kind='candidate') so the dashboard counts it."""
    store = _store(sf)
    hid = new_id("hyp")
    store.put(project_id, "candidate", hid,
              {"claim": claim, "statement": claim, "origin": "consejo", "by": persona},
              status="PROPOSED", actor=PERSONA_ACTOR.get(persona, persona),
              summary=claim[:120])
    return hid


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


def run_council(project_id: str, claim: str, *, sf: Any = None, loop: Any = None,
                hypothesis_id: str | None = None) -> dict[str, Any]:
    """Bohr dirige el ciclo AMBICIOSO sobre `claim` y registra el trabajo por personaje:
    Hilbert (hipótesis), Popper (resultado empírico/veredicto), Feynman (reformulaciones),
    Gödel/Euclides (lemas y contribuciones parciales verificadas). Un solo flujo → el
    dashboard y las fichas del Consejo se actualizan solos. Nada se infla: el veredicto y
    el estado 'partial_progress' salen tal cual del ResearchLoop."""
    from ..science.research_loop import ResearchLoop
    hid = hypothesis_id or record_hypothesis(project_id, claim, persona="hilbert", sf=sf)
    lp = loop or ResearchLoop()
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
    return {"hypothesis_id": hid, "disposition": disp, "final_verdict": final_v,
            "final_statement": final_stmt,
            "n_reformulations": len(seen) - 1,
            "contributions": res.get("contributions") or [],
            "lemma": res.get("lemma")}
