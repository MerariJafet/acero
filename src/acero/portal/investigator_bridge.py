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
