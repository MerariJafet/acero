"""Deep, multi-angle investigation: "Earth's place in the Universe".

Not a single narrow result — it works across several real angles, each backed by
REAL data analysis and/or REAL literature (Crossref, with retraction checks), records
everything as project artifacts with provenance, and synthesizes honest conclusions.
Makes NO discovery claim; the ceiling is human review.
"""

from __future__ import annotations

from typing import Any

from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

# Each angle: a sub-question + a literature query. Data-backed angles also run an analysis.
ANGLES = [
    {"key": "earth_orbit",
     "q": "¿La Tierra orbita el Sol y su órbita sigue leyes universales?",
     "lit": "Kepler third law exoplanets orbital period semi-major axis",
     "data": "kepler"},
    {"key": "sun_in_galaxy",
     "q": "¿Cómo y dónde se mueve el Sol dentro de la Vía Láctea?",
     "lit": "solar motion local standard of rest galactocentric distance"},
    {"key": "galaxy_in_cosmos",
     "q": "¿Cómo se mueve el Sistema Solar respecto al fondo cósmico de microondas?",
     "lit": "CMB dipole solar system peculiar velocity"},
    {"key": "cosmic_expansion",
     "q": "¿Cuál es la escala de expansión del universo y hay tensión entre métodos?",
     "lit": "Hubble tension H0 measurement discrepancy", "data": "hubble"},
    {"key": "are_we_typical",
     "q": "¿Ocupa la Tierra un lugar especial o típico? (principio copernicano)",
     "lit": "Copernican principle cosmological homogeneity"},
]


def _run_data(angle_key: str) -> dict[str, Any] | None:
    if angle_key == "kepler":
        from .kepler_law import verify
        return verify()
    if angle_key == "hubble":
        from .hubble_tension import analyze
        return analyze()
    return None


def _literature(query: str, rows: int = 3) -> list[dict[str, Any]]:
    from ..knowledge_mesh.connectors import crossref
    try:
        objs = crossref.search(query, rows=rows)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for o in objs:
        doi = (o.identifiers.get("doi") or [""])[0]
        # per-paper retraction check (real reverse lookup) for the top hit
        integ = o.integrity_status
        out.append({"title": o.title, "doi": doi, "type": o.object_type.value,
                    "integrity": integ, "url": o.canonical_url,
                    "authors": o.authors[:4]})
    return out


def investigate(project_id: str, *, session_factory: Any | None = None,
                synthesize: bool = True) -> dict[str, Any]:
    """Run the deep multi-angle investigation and record artifacts in the project."""
    sf = session_factory or default_session_factory()
    ledger = ResearchLedger(sf)
    if ledger.get_project(project_id) is None:
        return {"ok": False, "error": "project not found"}
    store = DiscoveryStore(sf, ledger)
    from ..world_model.graph import WorldModel
    from ..world_model.nodes import NodeType
    wm = WorldModel(sf, ledger, project_id)

    findings: list[dict[str, Any]] = []
    for a in ANGLES:
        data = _run_data(a["data"]) if a.get("data") else None
        papers = _literature(a["lit"])
        # record literature references as real artifacts (provenance-tracked)
        for pp in papers:
            if pp["doi"]:
                lid = new_id("lit")
                store.put(project_id, "literature", lid,
                          {"id": lid, "angle": a["key"], **pp}, status="INDEXED",
                          actor="knowledge_mesh", summary=f"paper: {pp['title'][:60]}")
        # record data analysis as a REAL experiment
        if data and data.get("ok"):
            eid = new_id("exp")
            store.put(project_id, "experiment", eid,
                      {"id": eid, "angle": a["key"], "kind": "real_data_analysis",
                       "synthetic": False, "result": data,
                       "claim": data.get("claim", "")}, status="COMPLETE",
                      actor="deep_investigation",
                      summary=f"real-data analysis: {a['key']}")
            wm.create(NodeType.CLAIM, (data.get("claim") or a["q"])[:90], confidence=0.55)
        findings.append({
            "angle": a["key"], "question": a["q"],
            "data_result": {k: data[k] for k in ("claim", "tension_sigma",
                            "consistent_with_kepler", "n_measurements", "n_planets")
                            if data and k in data} if data else None,
            "n_papers": len(papers),
            "papers": papers,
            "retracted_papers": [p for p in papers if p["integrity"] == "retracted"],
        })

    # honest synthesis (Codex) — labelled reasoning aid, not evidence
    synthesis = None
    if synthesize:
        synthesis = _synthesize(findings)

    # persist a dossier capturing the deep conclusions (incl. the synthesis text)
    did = new_id("dossier")
    store.put(project_id, "dossier", did,
              {"id": did, "kind": "deep_investigation",
               "readiness": "EXPLORATORY", "can_publish_automatically": False,
               "angles": [f["angle"] for f in findings],
               "synthesis": (synthesis or {}).get("text", ""),
               "n_papers": sum(f["n_papers"] for f in findings),
               "status": "AWAITING_HUMAN_REVIEW"},
              status="AWAITING_HUMAN_REVIEW", actor="deep_investigation",
              summary="dossier: investigación a fondo (nuestro lugar en el universo)")

    return {"ok": True, "project_id": project_id, "n_angles": len(findings),
            "findings": findings, "synthesis": synthesis, "dossier_id": did,
            "is_discovery": False,
            "honesty": ("Datos reales + literatura real con procedencia. Nada es un "
                        "descubrimiento; la síntesis IA es ayuda de razonamiento, no "
                        "evidencia; el techo es la revisión humana.")}


def _synthesize(findings: list[dict[str, Any]]) -> dict[str, Any]:
    from ..llm.providers import CodexCliProvider
    prov = CodexCliProvider(timeout_sec=200)
    if not prov.available():
        return {"provider": "unavailable", "text": ""}
    lines = []
    for f in findings:
        dr = f.get("data_result") or {}
        lines.append(f"- {f['question']} | datos: {dr.get('claim', dr) or 'solo literatura'} "
                     f"| {f['n_papers']} papers reales")
    prompt = (
        "Eres el Copiloto Científico de ACERO. Sintetiza HONESTAMENTE una conclusión "
        "multi-ángulo sobre 'el lugar de la Tierra en el universo' a partir de estos "
        "hallazgos reales (datos + literatura). Reglas: NO afirmes descubrimientos; "
        "distingue lo bien establecido de lo abierto; señala lo que NO se puede concluir; "
        "el techo es la revisión humana. Sé conciso y estructurado.\n\n"
        + "\n".join(lines))
    try:
        resp = prov.complete(prompt, temperature=0.2, max_tokens=1400)
        return {"provider": "codex", "text": resp.text,
                "disclaimer": "Síntesis IA: ayuda de razonamiento, NO evidencia."}
    except Exception as exc:  # noqa: BLE001
        return {"provider": "error", "text": str(exc)}
