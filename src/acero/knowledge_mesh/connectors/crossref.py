"""Crossref connector — real DOI metadata lookup with provenance + integrity status.

Crossref is an official aggregator that exposes bibliographic metadata, licenses,
funding and post-publication updates (corrections/retractions via Crossmark). This
connector fetches a work by DOI, normalizes it to a ScientificObject, and records
whether Crossref reports the work as retracted/corrected. It NEVER fabricates: a
DOI that Crossref does not return is reported as unverified, not invented.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..models import ObjectType, ScientificObject

_UA = "ACERO-knowledge-mesh/0.1 (mailto:merari.jafet@gmail.com)"
_BASE = "https://api.crossref.org/works/"

_TYPE_MAP = {
    "journal-article": ObjectType.PEER_REVIEWED_ARTICLE,
    "proceedings-article": ObjectType.PEER_REVIEWED_ARTICLE,
    "posted-content": ObjectType.PREPRINT,
    "dataset": ObjectType.DATASET,
    "book": ObjectType.REVIEW,
    "report": ObjectType.PEER_REVIEWED_ARTICLE,
}


class CrossrefError(RuntimeError):
    pass


def _get(url: str, *, timeout: float = 20.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def retraction_status(doi: str, *, timeout: float = 20.0) -> str:
    """REAL reverse lookup: does any work 'update' this DOI as a retraction/correction?

    Crossref stores post-publication updates on the NOTICE (which points back to the
    original via update-to), so a retracted paper is found by querying works that
    update it. Returns 'retracted' | 'corrected' | 'normal'.
    """
    url = f"{_BASE}?filter=updates:{urllib.parse.quote(doi)}&select=update-to,type&rows=20"
    try:
        items = _get(url, timeout=timeout).get("message", {}).get("items", []) or []
    except urllib.error.HTTPError:
        return "normal"
    status = "normal"
    for it in items:
        for upd in it.get("update-to", []) or []:
            label = str(upd.get("type", "")).lower()
            if upd.get("DOI", "").lower() != doi.lower():
                continue
            if "retract" in label:
                return "retracted"
            if "correct" in label or "erratum" in label:
                status = "corrected"
    return status


def lookup_doi(doi: str, *, timeout: float = 20.0, check_retraction: bool = True
               ) -> ScientificObject | None:
    """Return a normalized ScientificObject for a DOI, or None if Crossref lacks it."""
    doi = doi.strip().removeprefix("https://doi.org/").removeprefix("doi:").strip()
    if not doi:
        return None
    try:
        payload = _get(_BASE + urllib.parse.quote(doi), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise CrossrefError(f"crossref HTTP {e.code}") from e
    obj = _normalize(doi, payload.get("message", {}))
    if check_retraction and obj.integrity_status == "normal":
        rs = retraction_status(doi, timeout=timeout)
        if rs != "normal":
            obj.integrity_status = rs
            if rs == "retracted":
                obj.object_type = ObjectType.RETRACTED_WORK
            obj.add_provenance("integrity_auditor", rs,
                               "reverse Crossref lookup: an update notice targets this DOI")
    return obj


def search(query: str, *, rows: int = 5, timeout: float = 20.0) -> list[ScientificObject]:
    """Real bibliographic search via Crossref; returns normalized objects w/ provenance."""
    q = urllib.parse.quote(query.strip())
    url = f"{_BASE}?query.bibliographic={q}&rows={max(1, min(rows, 20))}&select=DOI,title,type,author,issued,license,subject,container-title,is-referenced-by-count,update-to,publisher"
    try:
        payload = _get(url, timeout=timeout)
    except urllib.error.HTTPError as e:
        raise CrossrefError(f"crossref search HTTP {e.code}") from e
    items = payload.get("message", {}).get("items", []) or []
    out: list[ScientificObject] = []
    for m in items:
        doi = str(m.get("DOI", "")).strip()
        if doi:
            out.append(_normalize(doi, m))
    return out


def _normalize(doi: str, m: dict[str, Any]) -> ScientificObject:
    ctype = str(m.get("type", "")).lower()
    otype = _TYPE_MAP.get(ctype, ObjectType.UNKNOWN)

    # integrity: Crossref lists post-publication updates in "update-to"
    integrity = "normal"
    for upd in m.get("update-to", []) or []:
        label = str(upd.get("type", "")).lower()
        if "retract" in label:
            integrity = "retracted"
            otype = ObjectType.RETRACTED_WORK
        elif "correct" in label and integrity != "retracted":
            integrity = "corrected"
    if str(m.get("update-policy", "")):
        pass  # crossmark policy present; not itself a retraction

    authors = [" ".join(x for x in [a.get("given"), a.get("family")] if x)
               for a in m.get("author", []) or []]
    institutions = sorted({aff.get("name", "")
                           for a in m.get("author", []) or []
                           for aff in a.get("affiliation", []) or [] if aff.get("name")})
    lic = {}
    for ld in m.get("license", []) or []:
        if ld.get("URL"):
            lic = {"url": ld["URL"], "content_version": ld.get("content-version")}
            break
    title = (m.get("title") or [""])[0]
    dates: dict[str, str] = {}
    for k in ("published-print", "published-online", "created", "deposited"):
        parts = (m.get(k) or {}).get("date-parts") or []
        if parts and parts[0]:
            dates[k] = "-".join(str(p) for p in parts[0])

    obj = ScientificObject(
        object_type=otype, title=title,
        identifiers={"doi": [doi]}, authors=authors, institutions=institutions,
        publication_dates=dates,
        topics=[s for s in (m.get("subject") or [])],
        license={**lic, "publisher": m.get("publisher", "")},
        access_status="metadata_only", source_id="crossref",
        canonical_url=f"https://doi.org/{doi}",
        review_status="peer_reviewed" if otype == ObjectType.PEER_REVIEWED_ARTICLE else "unknown",
        integrity_status=integrity,
        verification={"crossref": True, "container": (m.get("container-title") or [""])[0],
                      "is_referenced_by_count": m.get("is-referenced-by-count")},
    )
    obj.add_provenance("connector:crossref", "fetch_metadata", f"doi={doi}")
    if integrity != "normal":
        obj.add_provenance("integrity_auditor", integrity,
                           "Crossref reports a post-publication update")
    return obj
