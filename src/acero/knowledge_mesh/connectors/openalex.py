"""OpenAlex connector — relevance-ranked topical search WITH abstracts + concepts.

OpenAlex is an open scholarly index (CC0) that supports full-text relevance search
and returns concepts (topics) and a reconstructable abstract. This is far better for
TOPICAL literature discovery than a DOI-metadata lookup: results are ranked by
relevance and carry enough content (abstract) for a real analysis. Never fabricates:
a query with no results returns an empty list.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..models import ObjectType, ScientificObject

_UA = "ACERO-knowledge-mesh/0.1 (mailto:merari.jafet@gmail.com)"
_BASE = "https://api.openalex.org/works"

_TYPE_MAP = {
    "article": ObjectType.PEER_REVIEWED_ARTICLE,
    "preprint": ObjectType.PREPRINT,
    "dataset": ObjectType.DATASET,
    "review": ObjectType.REVIEW,
}


def _reconstruct_abstract(inv: dict[str, list[int]] | None) -> str:
    """OpenAlex stores abstracts as an inverted index {word: [positions]}."""
    if not inv:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)[:1500]


def _get(url: str, *, timeout: float = 25.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def search(query: str, *, rows: int = 5, min_year: int | None = None,
           timeout: float = 25.0) -> list[ScientificObject]:
    """Relevance-ranked topical search. Returns normalized objects with abstracts."""
    params = {"search": query.strip(), "per-page": str(max(1, min(rows, 25))),
              "sort": "relevance_score:desc"}
    flt = []
    if min_year:
        flt.append(f"from_publication_date:{min_year}-01-01")
    if flt:
        params["filter"] = ",".join(flt)
    url = f"{_BASE}?{urllib.parse.urlencode(params)}"
    try:
        items = _get(url, timeout=timeout).get("results", []) or []
    except urllib.error.HTTPError as e:  # pragma: no cover - network
        raise RuntimeError(f"openalex HTTP {e.code}") from e
    return [_normalize(w) for w in items]


def works_by_ids(ids: list[str], *, timeout: float = 25.0) -> list[ScientificObject]:
    """Fetch specific works (e.g. the REFERENCES of a paper) with abstracts."""
    out: list[ScientificObject] = []
    for wid in ids[:12]:
        wid = wid.strip().rsplit("/", 1)[-1]
        if not wid.startswith("W"):
            continue
        try:
            out.append(_normalize(_get(f"{_BASE}/{wid}", timeout=timeout)))
        except Exception:  # noqa: BLE001 - a missing reference is skipped, not faked
            continue
    return out


def _normalize(w: dict[str, Any]) -> ScientificObject:
    doi = (w.get("doi") or "").replace("https://doi.org/", "")
    otype = _TYPE_MAP.get(str(w.get("type", "")).lower(), ObjectType.PEER_REVIEWED_ARTICLE)
    if w.get("primary_location", {}).get("source", {}).get("type") == "repository":
        otype = ObjectType.PREPRINT
    authors = [a.get("author", {}).get("display_name", "")
               for a in w.get("authorships", []) or []][:6]
    concepts = [c.get("display_name", "") for c in (w.get("concepts") or [])
                if c.get("score", 0) > 0.3][:6]
    abstract = _reconstruct_abstract(w.get("abstract_inverted_index"))
    oa = w.get("open_access", {}) or {}
    ploc = w.get("primary_location", {}) or {}
    pdf_url = ploc.get("pdf_url") or oa.get("oa_url") or ""
    obj = ScientificObject(
        object_type=otype, title=w.get("title") or "",
        abstract=abstract or None,
        identifiers={"doi": [doi]} if doi else {"openalex": [w.get("id", "")]},
        authors=[a for a in authors if a], topics=concepts,
        publication_dates={"published": str(w.get("publication_date") or "")},
        license={"open_access": oa.get("is_oa"), "oa_status": oa.get("oa_status")},
        access_status="open" if oa.get("is_oa") else "metadata_only",
        source_id="openalex",
        canonical_url=(f"https://doi.org/{doi}" if doi else w.get("id", "")),
        review_status="peer_reviewed" if otype == ObjectType.PEER_REVIEWED_ARTICLE else "unknown",
        verification={"openalex": True, "cited_by_count": w.get("cited_by_count"),
                      "relevance_score": w.get("relevance_score"),
                      "openalex_id": (w.get("id") or "").rsplit("/", 1)[-1],
                      "is_oa": bool(oa.get("is_oa")), "pdf_url": pdf_url,
                      "referenced_works": [(x or "").rsplit("/", 1)[-1]
                                           for x in (w.get("referenced_works") or [])[:15]]},
    )
    obj.add_provenance("connector:openalex", "search",
                       f"relevance={w.get('relevance_score')}")
    return obj
