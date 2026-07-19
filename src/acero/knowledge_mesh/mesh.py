"""Scientific Retrieval Gateway (Phase 1 façade).

A single entry point for the mesh: list/verify sources, look up a DOI, and run a
real literature search — every result carries provenance and an epistemic type, and
nothing is invented. Later phases add semantic/graph retrieval and more connectors.
"""

from __future__ import annotations

from typing import Any

from . import sources as src
from .connectors import crossref


def list_sources() -> list[dict[str, Any]]:
    return [s.as_dict() for s in src.registry()]


def health_report(*, live: bool = False) -> dict[str, Any]:
    if live:
        return src.health_check_all()
    return {"n_sources": len(src.registry()),
            "note": "call with live=True to run real health checks"}


def lookup_doi(doi: str) -> dict[str, Any]:
    obj = crossref.lookup_doi(doi)
    if obj is None:
        return {"found": False, "doi": doi,
                "note": "Crossref returned no record — reported as unverified, not invented"}
    return {"found": True, "object": obj.as_dict(),
            "integrity_status": obj.integrity_status,
            "is_acero_generated": obj.is_acero_generated}


def search(query: str, *, rows: int = 5) -> dict[str, Any]:
    """Evidence-first literature search with provenance and query transparency."""
    results = crossref.search(query, rows=rows)
    return {
        "query": query, "sources_consulted": ["crossref"],
        "n_results": len(results),
        "results": [{"title": o.title, "doi": (o.identifiers.get("doi") or [""])[0],
                     "type": o.object_type.value, "review_status": o.review_status,
                     "integrity_status": o.integrity_status,
                     "url": o.canonical_url, "authors": o.authors[:5],
                     "license": o.license.get("url"), "date": o.publication_dates}
                    for o in results],
        "disclaimer": ("Evidencia recuperada de fuentes reales con procedencia. "
                       "Ninguna afirmación proviene de un modelo de lenguaje; "
                       "revisa retracciones/correcciones antes de citar."),
    }
