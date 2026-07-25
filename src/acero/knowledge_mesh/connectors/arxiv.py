"""arXiv connector — preprint search WITH full abstracts (physics/astro/math/cs/q-bio).

arXiv exposes an Atom search API. It is the primary source for physics/astronomy
preprints and returns the full abstract, which lets ACERO analyze real content. Never
fabricates: a query with no entries returns an empty list.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

from ..models import ObjectType, ScientificObject

_UA = "ACERO-knowledge-mesh/0.1 (+https://github.com/MerariJafet/acero)"
_BASE = "https://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"


def search(query: str, *, rows: int = 5, timeout: float = 25.0) -> list[ScientificObject]:
    params = {"search_query": f"all:{query.strip()}", "start": "0",
              "max_results": str(max(1, min(rows, 25))),
              "sortBy": "relevance", "sortOrder": "descending"}
    url = f"{_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        root = ET.fromstring(r.read())
    out: list[ScientificObject] = []
    for entry in root.findall(f"{_ATOM}entry"):
        out.append(_normalize(entry))
    return out


def _text(el, tag: str) -> str:
    node = el.find(f"{_ATOM}{tag}")
    return (node.text or "").strip() if node is not None else ""


def _normalize(entry) -> ScientificObject:
    arxiv_url = _text(entry, "id")
    arxiv_id = arxiv_url.rsplit("/abs/", 1)[-1]
    title = " ".join(_text(entry, "title").split())
    abstract = " ".join(_text(entry, "summary").split())[:1500]
    authors = [_text(a, "name") for a in entry.findall(f"{_ATOM}author")][:6]
    published = _text(entry, "published")[:10]
    doi = ""
    for link in entry.findall(f"{_ATOM}link"):
        if link.get("title") == "doi":
            doi = (link.get("href") or "").replace("http://dx.doi.org/", "")
    ids: dict[str, list[str]] = {"arxiv": [arxiv_id]}
    if doi:
        ids["doi"] = [doi]
    obj = ScientificObject(
        object_type=ObjectType.PREPRINT, title=title, abstract=abstract or None,
        identifiers=ids, authors=[a for a in authors if a],
        publication_dates={"published": published},
        license={"note": "arXiv per-submission license"}, access_status="open",
        source_id="arxiv", canonical_url=arxiv_url, review_status="preprint",
        verification={"arxiv": True},
    )
    obj.add_provenance("connector:arxiv", "search", f"arxiv={arxiv_id}")
    return obj
