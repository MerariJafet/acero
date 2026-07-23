"""Data resolver — turn dataset REFERENCES into real, fetchable URLs.

The factory used to fail at the fetch stage whenever Codex named a dataset (e.g.
"GEO GSE111629") without giving a concrete downloadable URL. This resolver maps
common public-repository ACCESSIONS to their real, deterministic download URLs,
so "download_data" experiments actually get real data instead of staying a PLAN.

Every resolver targets an ALLOWLISTED host and returns a URL that a plain HTTPS
GET can retrieve. Unknown references resolve to nothing (honest: no fake URLs).
"""

from __future__ import annotations

import re
import urllib.request
from typing import Any

_UA = "ACERO-data-resolver/0.1 (mailto:merari.jafet@gmail.com)"

# accession patterns → resolver
_GEO_RE = re.compile(r"\bGSE(\d{3,})\b", re.I)


def _geo_series_matrix_url(acc: str) -> str:
    """GEO series-matrix files live at a deterministic FTP path."""
    acc = acc.upper()
    num = acc[3:]
    stub = "GSE" + (num[:-3] + "nnn" if len(num) > 3 else "nnn")
    return (f"https://ftp.ncbi.nlm.nih.gov/geo/series/{stub}/{acc}/matrix/"
            f"{acc}_series_matrix.txt.gz")


def _url_ok(url: str, *, timeout: float = 25.0, opener: Any | None = None) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        op = opener or urllib.request.urlopen
        with op(req, timeout=timeout) as r:            # small GET, we only need 1 byte
            return bool(r.read(1))
    except Exception:  # noqa: BLE001
        return False


def resolve_reference(text: str, *, verify: bool = True,
                      opener: Any | None = None) -> dict[str, Any] | None:
    """Find a known accession in free text and return a real download spec."""
    m = _GEO_RE.search(text or "")
    if m:
        acc = "GSE" + m.group(1)
        url = _geo_series_matrix_url(acc)
        if not verify or _url_ok(url, opener=opener):
            return {"url": url, "filename": f"{acc}_series_matrix.txt.gz",
                    "accession": acc, "repository": "GEO",
                    "what": f"GEO series matrix de {acc} (metadatos + matriz)"}
    return None


def enrich_plan_urls(plan: dict[str, Any], *, verify: bool = True,
                     opener: Any | None = None) -> dict[str, Any]:
    """Fill in missing/placeholder data URLs from accessions the plan mentions.

    Codex often gives an accession or a dataset name but no URL, or a URL that is
    not directly fetchable. For each declared dataset we try to resolve a real
    URL; we also scan the analysis outline for accessions when no URL exists.
    """
    urls = list(plan.get("data_urls") or [])
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in urls:
        acc = str(spec.get("accession") or "")
        url = str(spec.get("url") or "").strip()
        # a spec that already has a directly-fetchable http(s) file URL is kept
        if url.lower().startswith("https://") and not acc:
            if url not in seen:
                seen.add(url)
                out.append(spec)
            continue
        ref = acc or url or str(spec.get("what") or "")
        r = resolve_reference(ref, verify=verify, opener=opener)
        if r and r["url"] not in seen:
            seen.add(r["url"])
            out.append({**r, "what": spec.get("what") or r["what"]})
        elif url.lower().startswith("https://") and url not in seen:
            seen.add(url)
            out.append(spec)
    # if the plan declared NO usable URL, mine the outline for accessions
    if not out:
        r = resolve_reference(str(plan.get("analysis_outline") or ""),
                              verify=verify, opener=opener)
        if r:
            out.append(r)
    return {**plan, "data_urls": out}
