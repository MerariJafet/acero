"""Data resolver — turn dataset REFERENCES into real, fetchable URLs.

The factory used to fail at the fetch stage whenever Codex named a dataset (e.g.
"GEO GSE111629") without giving a concrete downloadable URL. This resolver maps
common public-repository ACCESSIONS to their real, deterministic download URLs,
so "download_data" experiments actually get real data instead of staying a PLAN.

Every resolver targets an ALLOWLISTED host and returns a URL that a plain HTTPS
GET can retrieve. Unknown references resolve to nothing (honest: no fake URLs).
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any

_UA = "ACERO-data-resolver/0.1 (mailto:merari.jafet@gmail.com)"

# accession patterns → resolver
_GEO_RE = re.compile(r"\bGSE(\d{3,})\b", re.I)
_ZENODO_RE = re.compile(r"(?:zenodo\.org/records?/|zenodo[:\s]+|10\.5281/zenodo\.)(\d{4,})",
                        re.I)


_FIGSHARE_RE = re.compile(r"(?:figshare\.com/articles/[\w/]*?/|figshare[:\s]+"
                          r"|10\.6084/m9\.figshare\.)(\d{5,})", re.I)
_DRYAD_RE = re.compile(r"(?:datadryad\.org/[\w/]*|dryad[:\s]+|10\.5061/dryad\.)"
                       r"([\w.]+)", re.I)


def _get_json(url: str, opener: Any | None, timeout: float = 25.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/json"})
    op = opener or urllib.request.urlopen
    with op(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def figshare_files(article_id: str, *, opener: Any | None = None
                   ) -> list[dict[str, Any]]:
    """Figshare article → its downloadable data files (open, no auth to read)."""
    try:
        d = _get_json(f"https://api.figshare.com/v2/articles/{article_id}", opener)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for f in (d.get("files") or []):
        name, url = f.get("name") or "", f.get("download_url") or ""
        if name and url and name.lower().endswith(
                (".csv", ".tsv", ".txt", ".json", ".gz", ".zip", ".dat", ".h5",
                 ".npy", ".fits")):
            out.append({"url": url, "filename": name, "accession": article_id,
                        "repository": "Figshare", "bytes_hint": f.get("size"),
                        "is_data": bool(_DATA_HINT.search(name)),
                        "what": f"Figshare {article_id}: {name}"})
    out.sort(key=lambda f: not f["is_data"])
    return out


def dryad_download(doi_suffix: str, *, opener: Any | None = None
                   ) -> list[dict[str, Any]]:
    """Dryad dataset → its download bundle (a zip; the sandbox unzips with zipfile)."""
    doi = f"doi:10.5061/dryad.{doi_suffix}" if not doi_suffix.startswith("doi:") \
        else doi_suffix
    enc = urllib.parse.quote(doi, safe="")
    try:
        d = _get_json(f"https://datadryad.org/api/v2/datasets/{enc}", opener)
    except Exception:  # noqa: BLE001
        return []
    href = ((d.get("_links") or {}).get("stash:download") or {}).get("href")
    if not href:
        return []
    return [{"url": "https://datadryad.org" + href,
             "filename": f"dryad_{doi_suffix.replace('.', '_')}.zip",
             "accession": doi, "repository": "Dryad", "is_data": True,
             "what": f"Dryad {doi}: bundle de datos (zip)"}]


def zenodo_files(record_id: str, *, timeout: float = 25.0,
                 opener: Any | None = None) -> list[dict[str, Any]]:
    """List downloadable files of a Zenodo record via its public API.

    Zenodo hosts a huge amount of open scientific data (incl. quantum-computing
    benchmark/QEC datasets); the record's files have direct download URLs.
    """
    api = f"https://zenodo.org/api/records/{record_id}"
    try:
        req = urllib.request.Request(api, headers={"User-Agent": _UA,
                                                   "Accept": "application/json"})
        op = opener or urllib.request.urlopen
        with op(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    out = []
    for f in (data.get("files") or []):
        name = f.get("key") or f.get("filename") or ""
        url = ((f.get("links") or {}).get("self")
               or (f.get("links") or {}).get("download") or "")
        if name and url and name.lower().endswith(
                (".csv", ".tsv", ".txt", ".json", ".gz", ".zip", ".dat", ".h5", ".npy")):
            out.append({"url": url, "filename": name, "accession": record_id,
                        "repository": "Zenodo",
                        "is_data": bool(_DATA_HINT.search(name)),
                        "bytes_hint": f.get("size"),
                        "what": f"Zenodo {record_id}: {name}"})
    out.sort(key=lambda f: not f["is_data"])
    return out

# NASA Exoplanet Archive TAP: build a real CSV query URL from a table reference
_NEA_BASE = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
_NEA_TABLES = {
    # confirmed-planet composite parameters (radii, periods, stellar params)
    "pscomppars": ("pl_name,hostname,pl_rade,pl_radeerr1,pl_radeerr2,pl_orbper,"
                   "pl_bmasse,st_teff,st_rad,st_mass,sy_kepmag,sy_gaiamag,"
                   "disc_facility,discoverymethod"),
    # Kepler DR25 KOI table (the classic radius-valley sample) — verified columns
    "q1_q17_dr25_koi": ("kepoi_name,koi_disposition,koi_prad,koi_prad_err1,"
                        "koi_prad_err2,koi_period,koi_steff,koi_srad,koi_kepmag,"
                        "koi_model_snr,koi_score"),
}


def _nea_url(table: str) -> str:
    cols = _NEA_TABLES[table]
    q = f"select {cols} from {table}".replace(" ", "+").replace(",", ",")
    return f"{_NEA_BASE}?query={q}&format=csv"


def _resolve_nea(text: str) -> list[dict[str, Any]]:
    t = (text or "").lower()
    exo = any(k in t for k in ("exoplanet archive", "nasa exoplanet", "koi",
                               "confirmed planet", "pscomppars", "kepler objects",
                               "radius valley", "valle de radios", "dr25", "exoplaneta"))
    chem = any(k in t for k in ("abundanc", "abundance", "chemical", "química estelar",
                                "quimica estelar", "mg/si", "fe/h fino", "hypatia",
                                "elemental", "composición estelar", "composicion estelar"))
    specs: list[dict[str, Any]] = []
    # a chemistry cross-match STILL needs the planet radii table — you can't test
    # radius-vs-chemistry without the radii. So chemistry implies the planet table.
    if exo or chem:
        if any(k in t for k in ("koi", "dr25", "kepler objects", "cumulative")):
            specs.append({"url": _nea_url("q1_q17_dr25_koi"),
                          "filename": "kepler_dr25_koi.csv",
                          "accession": "q1_q17_dr25_koi", "repository": "NASA-NEA",
                          "what": "Kepler DR25 KOI (radios, periodos, disposición, SNR)"})
        specs.append({"url": _nea_url("pscomppars"),
                      "filename": "nea_confirmed_planets.csv",
                      "accession": "pscomppars", "repository": "NASA-NEA",
                      "what": "NASA Exoplanet Archive planetas confirmados (radios±, "
                              "periodos, hostname para CRUZAR con la química estelar)"})
    # CROSS-CATALOG: stellar chemical abundances (join by host star) — the
    # discovery-shaped angle that few have combined with planet radii.
    if chem:
        specs.append({
            "url": ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
                    "select+hostname,st_met,st_teff,st_logg,st_mass,st_rad,st_age"
                    "+from+stellarhosts&format=csv"),
            "filename": "nea_stellar_hosts.csv", "accession": "stellarhosts",
            "repository": "NASA-NEA",
            "what": "Parámetros estelares de anfitriones (metalicidad, Teff, logg) "
                    "para CRUZAR con radios planetarios por hostname"})
    return specs


def _geo_stub(acc: str) -> str:
    acc = acc.upper()
    num = acc[3:]
    return "GSE" + (num[:-3] + "nnn" if len(num) > 3 else "nnn")


def _geo_series_matrix_url(acc: str) -> str:
    """GEO series-matrix files (metadata, sometimes the data) — deterministic path."""
    acc = acc.upper()
    return (f"https://ftp.ncbi.nlm.nih.gov/geo/series/{_geo_stub(acc)}/{acc}/matrix/"
            f"{acc}_series_matrix.txt.gz")


# supplementary data files that ARE the real numeric matrix (betas / expression)
_DATA_HINT = re.compile(
    r"(normali[sz]|processed|beta|methylation|matrix|series_matrix|expression|"
    r"counts|abundance|values|level3|signal)", re.I)
_SKIP = re.compile(r"(RAW\.tar|filelist|README|annot|\.idat|\.pdf|\.xlsx?$)", re.I)


def geo_supplementary_files(acc: str, *, timeout: float = 30.0,
                            opener: Any | None = None) -> list[dict[str, Any]]:
    """List GEO supplementary files and rank the ones that hold the real matrix.

    For big arrays (450K methylation, RNA-seq) the processed data matrix lives in
    /suppl/ — this is where a STRONG reanalysis gets its actual numbers.
    """
    acc = acc.upper()
    url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{_geo_stub(acc)}/{acc}/suppl/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        op = opener or urllib.request.urlopen
        with op(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return []
    files = []
    for name in re.findall(r'href="([^"?/][^"]*\.(?:gz|csv|txt|tsv))"', html):
        if _SKIP.search(name):
            continue
        files.append({"url": url + name, "filename": name,
                      "accession": acc, "repository": "GEO",
                      "is_data": bool(_DATA_HINT.search(name)),
                      "what": f"GEO {acc} suppl: {name}"})
    # data-matrix files first, then the rest
    files.sort(key=lambda f: not f["is_data"])
    return files


def _url_ok(url: str, *, timeout: float = 25.0, opener: Any | None = None) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        op = opener or urllib.request.urlopen
        with op(req, timeout=timeout) as r:            # small GET, we only need 1 byte
            return bool(r.read(1))
    except Exception:  # noqa: BLE001
        return False


def resolve_reference(text: str, *, verify: bool = True, want_data: bool = False,
                      opener: Any | None = None) -> list[dict[str, Any]]:
    """Find an accession in free text → real download spec(s).

    Default: the series matrix (metadata, small). want_data=True also pulls the
    processed DATA matrix from /suppl/ (the real betas/expression) — that's what a
    strong reanalysis needs; storage/RAM permitting (both configurable).
    """
    zen = _ZENODO_RE.search(text or "")
    if zen:
        files = zenodo_files(zen.group(1), opener=opener)
        if files:
            data = [f for f in files if f["is_data"]][:3]
            return (data or files[:2])
    fig = _FIGSHARE_RE.search(text or "")
    if fig:
        files = figshare_files(fig.group(1), opener=opener)
        if files:
            data = [f for f in files if f["is_data"]][:3]
            return (data or files[:2])
    dry = _DRYAD_RE.search(text or "")
    if dry:
        files = dryad_download(dry.group(1), opener=opener)
        if files:
            return files
    nea = _resolve_nea(text)
    if nea:
        return nea
    m = _GEO_RE.search(text or "")
    if not m:
        return []
    acc = "GSE" + m.group(1)
    specs: list[dict[str, Any]] = []
    smx = _geo_series_matrix_url(acc)
    if not verify or _url_ok(smx, opener=opener):
        specs.append({"url": smx, "filename": f"{acc}_series_matrix.txt.gz",
                      "accession": acc, "repository": "GEO",
                      "what": f"GEO {acc} series matrix (metadatos + fenotipos)"})
    if want_data:
        for f in geo_supplementary_files(acc, opener=opener):
            if f["is_data"]:
                specs.append(f)         # the real numeric matrix (betas/expression)
                break
    return specs


def enrich_plan_urls(plan: dict[str, Any], *, verify: bool = True,
                     want_data: bool = False,
                     opener: Any | None = None) -> dict[str, Any]:
    """Fill in missing/placeholder data URLs from accessions the plan mentions.

    Codex often gives an accession or a dataset name but no fetchable URL. We
    resolve real URLs; with want_data=True we also pull the processed data matrix
    (real betas/expression) from the repository's supplementary files.
    """
    urls = list(plan.get("data_urls") or [])
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(spec: dict[str, Any]) -> None:
        u = str(spec.get("url") or "")
        if u and u not in seen:
            seen.add(u)
            out.append(spec)

    for spec in urls:
        acc = str(spec.get("accession") or "")
        url = str(spec.get("url") or "").strip()
        if url.lower().startswith("https://") and not acc:
            _add(spec)                       # already a direct fetchable file URL
            continue
        ref = acc or url or str(spec.get("what") or "")
        resolved = resolve_reference(ref, verify=verify, want_data=want_data,
                                     opener=opener)
        if resolved:
            human = str(spec.get("what") or "")
            for i, r in enumerate(resolved):
                # keep the human description on the primary (series-matrix) spec
                _add({**r, "what": (human if i == 0 and human else r["what"])})
        elif url.lower().startswith("https://"):
            _add(spec)
    if not out:                              # mine the outline for an accession
        for r in resolve_reference(str(plan.get("analysis_outline") or ""),
                                   verify=verify, want_data=want_data, opener=opener):
            _add(r)
    return {**plan, "data_urls": out}
