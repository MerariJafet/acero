"""Scientific Retrieval Gateway (Phase 1 façade).

A single entry point for the mesh: list/verify sources, look up a DOI, and run a
real literature search — every result carries provenance and an epistemic type, and
nothing is invented. Later phases add semantic/graph retrieval and more connectors.
"""

from __future__ import annotations

from typing import Any

from . import sources as src
from .connectors import arxiv, crossref, openalex


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


def topical_search(query: str, *, domain: str = "", rows: int = 6) -> list[dict[str, Any]]:
    """Relevance-ranked, multi-source TOPICAL search WITH abstracts.

    Uses OpenAlex (relevance + abstracts + concepts) as primary; adds arXiv for
    physics/astronomy/math/cs preprints; falls back to Crossref. De-duplicates by DOI/
    title. This is what real literature discovery should use — not a bare DOI lookup.
    """
    objs: list[Any] = []
    try:
        objs += openalex.search(query, rows=rows)
    except Exception:  # noqa: BLE001
        pass
    if any(k in (domain or "").lower() for k in ("physics", "astro", "math", "quant", "cs")) \
            or not objs:
        try:
            objs += arxiv.search(query, rows=max(2, rows // 2))
        except Exception:  # noqa: BLE001
            pass
    if not objs:
        try:
            objs += crossref.search(query, rows=rows)
        except Exception:  # noqa: BLE001
            pass
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for o in objs:
        doi = (o.identifiers.get("doi") or [""])[0]
        key = doi or (o.title or "").lower()[:60]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"title": o.title, "doi": doi, "type": o.object_type.value,
                    "integrity": o.integrity_status, "url": o.canonical_url,
                    "authors": o.authors[:4], "abstract": o.abstract or "",
                    "topics": o.topics[:5], "source": o.source_id,
                    "relevance": o.verification.get("relevance_score"),
                    "openalex_id": o.verification.get("openalex_id", ""),
                    "is_oa": o.verification.get("is_oa", False),
                    "pdf_url": o.verification.get("pdf_url", ""),
                    "referenced_works": o.verification.get("referenced_works", [])})
    return out[:rows]


def snowball(reference_ids: list[str], *, rows: int = 10) -> list[dict[str, Any]]:
    """Level-2 literature: fetch the REFERENCES of already-read papers (real
    citation-following, with abstracts). Empty result = none resolvable."""
    objs = openalex.works_by_ids(reference_ids[: rows + 4])
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for o in objs:
        doi = (o.identifiers.get("doi") or [""])[0]
        key = doi or (o.title or "").lower()[:60]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"title": o.title, "doi": doi, "type": o.object_type.value,
                    "integrity": o.integrity_status, "url": o.canonical_url,
                    "authors": o.authors[:4], "abstract": o.abstract or "",
                    "topics": o.topics[:5], "source": o.source_id,
                    "relevance": o.verification.get("relevance_score"),
                    "openalex_id": o.verification.get("openalex_id", ""),
                    "referenced_works": o.verification.get("referenced_works", [])})
    return out[:rows]


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
