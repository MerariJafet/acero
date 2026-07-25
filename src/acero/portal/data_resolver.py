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

# PubChem PUG-REST — free, no key. A chemistry structure-property study fetches a
# reproducible table of physicochemical descriptors for a DEFINED set of compounds.
_PUBCHEM_HINT = re.compile(
    r"\bpubchem\b|pug[-\s]?rest|\bcids?\b|drug-?like|lipinski|"
    r"molecular (?:propert|descriptor|weight)|\bxlogp\b|\btpsa\b|\blogp\b|"
    r"h-?bond|structure[-\s]property|physicochem|fisicoquím|descriptor(?:es)?\s+molecular",
    re.I)
_CID_RE = re.compile(r"\bcids?[:\s]*([\d,\s]+)", re.I)
# descriptors present for the vast majority of small molecules
_PUBCHEM_PROPS = ("MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,"
                  "RotatableBondCount,HeavyAtomCount,Complexity,Charge,"
                  "MolecularFormula,CanonicalSMILES")

# ChEMBL REST (EBI) — free, no key. MEASURED bioactivities (IC50/Ki/EC50/Kd) with
# structures: the endpoint PubChem can't give. This is structure-ACTIVITY, real
# assay data, not computed descriptors.
_CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"
_CHEMBL_ID_RE = re.compile(r"\b(CHEMBL\d+)\b", re.I)
_CHEMBL_HINT = re.compile(
    r"\bchembl\b|\bic50\b|\bki\b|\bec50\b|\bkd\b|bioact|bioassay|bioensayo|"
    r"potency|potencia|binding affinity|afinidad|structure[-\s]activity|\bsar\b|"
    r"pchembl|dose[-\s]response|dosis[-\s]respuesta|inhibitor|inhibidor", re.I)
_CHEMBL_STD_TYPES = ("IC50", "Ki", "EC50", "Kd", "Potency")


def chembl_activity_url(chembl_id: str, standard_type: str = "IC50",
                        field: str = "target_chembl_id", limit: int = 1000) -> str:
    """PUG-style URL for MEASURED activities of a target/molecule as JSON."""
    return (f"{_CHEMBL_BASE}/activity.json?{field}={chembl_id}"
            f"&standard_type={standard_type}&limit={limit}")


def chembl_target_search(name: str, *, opener: Any | None = None) -> str:
    """Resolve a target NAME (e.g. 'EGFR') to a CHEMBL target id, preferring a
    single protein (search[0] can be a protein complex)."""
    if not name:
        return ""
    url = f"{_CHEMBL_BASE}/target/search.json?q={urllib.parse.quote(name)}&limit=8"
    try:
        d = _get_json(url, opener)
    except Exception:  # noqa: BLE001
        return ""
    targs = d.get("targets") or []
    for tt in targs:
        if tt.get("target_type") == "SINGLE PROTEIN":
            return str(tt.get("target_chembl_id") or "")
    return str((targs[0].get("target_chembl_id") if targs else "") or "")


def _detect_std_type(t: str) -> str:
    for s in _CHEMBL_STD_TYPES:
        if re.search(rf"\b{s}\b", t, re.I):
            return s
    return "IC50"


def _resolve_chembl(text: str, *, opener: Any | None = None) -> list[dict[str, Any]]:
    """Chemistry/pharmacology MEASURED bioactivity from ChEMBL — real, free.

    Needs an explicit CHEMBL id (target by default; molecule if the text says so)
    or a named target we can search. Otherwise silent (no arbitrary dump).
    """
    t = text or ""
    if not (_CHEMBL_HINT.search(t) or _CHEMBL_ID_RE.search(t)):
        return []
    std = _detect_std_type(t)
    idm = _CHEMBL_ID_RE.search(t)
    if idm:
        cid = idm.group(1).upper()
        pre = t[max(0, idm.start() - 25):idm.start()].lower()
        if any(k in pre for k in ("molecul", "compound", "molécul", "fármaco",
                                  "ligand", "drug")):
            field, label = "molecule_chembl_id", f"molécula {cid}"
        else:
            field, label = "target_chembl_id", f"diana {cid}"
        target = cid
    else:
        nm = re.search(r"(?:target|diana|prote[ií]na|receptor|enzima)[:\s]+"
                       r"([A-Za-z0-9][A-Za-z0-9\- ]{1,38})", t, re.I)
        target = chembl_target_search(nm.group(1).strip(), opener=opener) if nm else ""
        field, label = "target_chembl_id", f"diana {target}"
        if not target:
            return []
    return [{"url": chembl_activity_url(target, std, field),
             "filename": f"chembl_{target}_{std}.json", "accession": target,
             "repository": "ChEMBL", "is_data": True,
             "what": (f"ChEMBL: actividades {std} MEDIDAS para {label} (canonical_smiles, "
                      f"standard_value/units, pchembl_value, molecule_chembl_id) — "
                      f"bioensayos reales, ≤1000 registros (JSON)")}]


# TDC (Therapeutics Data Commons) ADME/Tox — curated single-task datasets on Harvard
# Dataverse. Each is a tab file "Drug_ID  Drug(SMILES)  Y(measured endpoint)". This is
# the MEASURED ADME/Tox layer (e.g. Caco-2 permeability) PubChem/ChEMBL don't cover.
# IDs verified by real download (all return the expected Drug/SMILES/Y header).
_TDC_BASE = "https://dataverse.harvard.edu/api/access/datafile/"
_TDC_IDS = {
    "caco2_wang": 4259569, "solubility_aqsoldb": 4259610,
    "lipophilicity_astrazeneca": 4259595, "bbb_martins": 4259566,
    "hia_hou": 4259591, "bioavailability_ma": 4259567,
    "pgp_broccatelli": 4259597, "ppbr_az": 6413140, "vdss_lombardo": 4267387,
    "half_life_obach": 4266799, "clearance_hepatocyte_az": 4266187,
    "clearance_microsome_az": 4266186, "herg": 4259588, "ames": 4259564,
    "dili": 4259585, "ld50_zhu": 4267146, "cyp2d6_veith": 4259580,
    "cyp3a4_veith": 4259582, "cyp2c9_veith": 4259577, "pampa_ncats": 6695858,
    "hydrationfreeenergy_freesolv": 4259594, "skin_reaction": 4259609,
}
# STRONG aliases: dataset-specific terms that map on their own (fire w/o extra context).
_TDC_STRONG = [
    (r"caco-?2", "caco2_wang"), (r"pampa", "pampa_ncats"),
    (r"\bbbb\b|blood-?brain|barrera hematoencef", "bbb_martins"),
    (r"p-?gp\b|p-?glyco|glicoprote[ií]na p", "pgp_broccatelli"),
    (r"\bherg\b|cardiotox", "herg"), (r"\bames\b|mutagen", "ames"),
    (r"\bdili\b|hepatotox|liver injury|da[nñ]o hep", "dili"),
    (r"\bld50\b", "ld50_zhu"), (r"\bvdss\b", "vdss_lombardo"),
    (r"\bppbr\b", "ppbr_az"), (r"freesolv|hydration free energy", "hydrationfreeenergy_freesolv"),
    (r"cyp\s?2d6", "cyp2d6_veith"), (r"cyp\s?3a4", "cyp3a4_veith"),
    (r"cyp\s?2c9", "cyp2c9_veith"), (r"\bhia\b|intestinal absorption|absorci[oó]n intestinal",
                                     "hia_hou"),
    (r"bioavailab|biodisponib", "bioavailability_ma"),
    (r"aqsol", "solubility_aqsoldb"),
]
# WEAK aliases: generic terms; only route to TDC when an ADME/Tox/dataset context exists,
# so they don't steal a PubChem-descriptor or unrelated request.
_TDC_WEAK = [
    (r"solubilit|solubilidad", "solubility_aqsoldb"),
    (r"permeab", "caco2_wang"),
    (r"lipophilic|lipofilic|logd\b", "lipophilicity_astrazeneca"),
    (r"plasma protein bind|uni[oó]n a prote[ií]nas", "ppbr_az"),
    (r"volume of distribution|volumen de distribuci", "vdss_lombardo"),
    (r"half-?life|vida media", "half_life_obach"),
    (r"hepatocyte clearance|aclaramiento hepatoc", "clearance_hepatocyte_az"),
    (r"microsom", "clearance_microsome_az"),
    (r"\bclearance\b|aclaramiento", "clearance_hepatocyte_az"),
    (r"skin reaction|reacci[oó]n cut[aá]nea|irritaci", "skin_reaction"),
]
_TDC_CTX = re.compile(r"\btdc\b|therapeutics data commons|\badme[t]?\b|\btox|dataset|"
                      r"benchmark|experimental|medid|measured|endpoint", re.I)


def tdc_dataset_url(name: str) -> str:
    return f"{_TDC_BASE}{_TDC_IDS[name]}"


def _resolve_tdc(text: str) -> list[dict[str, Any]]:
    """Map an ADME/Tox request to a verified TDC dataset (SMILES + measured Y)."""
    t = text or ""
    tl = t.lower()
    name = ""
    for n in _TDC_IDS:                       # explicit dataset name wins
        if n in tl:
            name = n
            break
    if not name:
        for pat, n in _TDC_STRONG:
            if re.search(pat, t, re.I):
                name = n
                break
    if not name and _TDC_CTX.search(t):
        for pat, n in _TDC_WEAK:
            if re.search(pat, t, re.I):
                name = n
                break
    if not name:
        return []
    return [{"url": tdc_dataset_url(name), "filename": f"tdc_{name}.tab",
             "accession": f"tdc:{name}", "repository": "TDC", "is_data": True,
             "what": (f"TDC {name} (Therapeutics Data Commons / Harvard Dataverse): "
                      f"tabla tab-separada Drug_ID + Drug(SMILES) + Y (endpoint ADME/Tox "
                      f"MEDIDO); split estándar del benchmark")}]


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


def pubchem_property_url(cids: list[int]) -> str:
    """PUG-REST URL for a physicochemical-descriptor CSV over an explicit CID list."""
    ids = ",".join(str(c) for c in cids)
    return (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{ids}/property/"
            f"{_PUBCHEM_PROPS}/CSV")


def _resolve_pubchem(text: str, *, n_default: int = 250) -> list[dict[str, Any]]:
    """Chemistry structure-property data from PubChem — real, free, reproducible.

    Either an explicit CID list in the text, or a DEFINED sample (CIDs 1..N) so the
    dataset is deterministic and re-fetchable. PUG-REST GET caps at a few hundred
    CIDs, so N is bounded. Honest scope: these are computed descriptors (MW, XLogP,
    TPSA, H-bond counts, …), NOT measured bioassay endpoints.
    """
    t = text or ""
    if not _PUBCHEM_HINT.search(t):
        return []
    cids: list[int] = []
    m = _CID_RE.search(t)
    if m:
        cids = [int(x) for x in re.findall(r"\d+", m.group(1))][:400]
    contiguous = not cids
    if not cids:
        n = n_default
        mnum = re.search(r"(\d{2,4})\s*(?:compuestos|mol[eé]culas|compounds|"
                         r"molecules|cids?)", t, re.I)
        if mnum:
            n = max(20, min(400, int(mnum.group(1))))
        cids = list(range(1, n + 1))
    acc = f"pubchem-cid-1..{cids[-1]}" if contiguous else "pubchem-cids"
    return [{"url": pubchem_property_url(cids),
             "filename": "pubchem_properties.csv", "accession": acc,
             "repository": "PubChem", "is_data": True,
             "what": (f"PubChem PUG-REST: descriptores fisicoquímicos (MW, XLogP, TPSA, "
                      f"HBD/HBA, rotables, complejidad, fórmula, SMILES) de {len(cids)} "
                      f"compuestos — descriptores calculados, no ensayos medidos")}]


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
    # STELLAR chemistry only — must have an ASTRONOMY signal, else generic
    # molecular "chemical/elemental" (drug chemistry!) would wrongly pull NASA data.
    astro = exo or any(k in t for k in ("stellar", "estelar", "star", "estrella",
                                        "host star", "planet host", "kepler", "tess",
                                        "gaia", "metallicity", "metalicidad"))
    chem = astro and any(k in t for k in (
        "abundanc", "abundance", "química estelar", "quimica estelar", "mg/si",
        "fe/h", "hypatia", "composición estelar", "composicion estelar",
        "stellar chemistry", "abundancias"))
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


# which domains each domain-specific repository serves (generalist repos serve all)
_DOMAIN_REPOS = {
    "nea": ("astronomy", "physics"),
    "geo": ("genetics", "genomics", "biology", "medicine", "chemistry"),
    "pubchem": ("chemistry", "biology", "medicine", "genetics", "genomics",
                "biochemistry", "pharmacology"),
    "chembl": ("chemistry", "biology", "medicine", "biochemistry", "pharmacology"),
    "tdc": ("chemistry", "biology", "medicine", "biochemistry", "pharmacology",
            "toxicology"),
}


def _domain_ok(repo: str, domain: str) -> bool:
    """A domain-specific resolver only fires for its domains; blank domain = allow."""
    if not domain:
        return True
    allowed = _DOMAIN_REPOS.get(repo)
    return allowed is None or domain.lower() in allowed


# hosts that only serve a specific science domain — a direct URL to one of these
# is dropped when the project domain doesn't match (anti-contamination for the
# case where Codex hard-codes e.g. an exoplanetarchive URL in a chemistry plan).
_HOST_DOMAINS = {
    "exoplanetarchive.ipac.caltech.edu": ("astronomy", "physics"),
    "mast.stsci.edu": ("astronomy", "physics"),
    "irsa.ipac.caltech.edu": ("astronomy", "physics"),
    "vizier.cds.unistra.fr": ("astronomy", "physics"),
    "vizier.u-strasbg.fr": ("astronomy", "physics"),
    "simbad.cds.unistra.fr": ("astronomy", "physics"),
    "gea.esac.esa.int": ("astronomy", "physics"),
    "gwosc.org": ("astronomy", "physics"),
    "pubchem.ncbi.nlm.nih.gov": ("chemistry", "biology", "medicine", "genetics",
                                 "genomics", "biochemistry", "pharmacology"),
}


def _host_domain_ok(url: str, domain: str) -> bool:
    """A direct URL to a domain-specific host is only allowed for its domains."""
    if not domain:
        return True
    try:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return True
    for h, allowed in _HOST_DOMAINS.items():
        if host == h or host.endswith("." + h):
            return domain.lower() in allowed
    return True


def resolve_reference(text: str, *, verify: bool = True, want_data: bool = False,
                      domain: str = "", opener: Any | None = None
                      ) -> list[dict[str, Any]]:
    """Find an accession in free text → real download spec(s).

    Default: the series matrix (metadata, small). want_data=True also pulls the
    processed DATA matrix from /suppl/. `domain` gates domain-specific resolvers so
    a chemistry project never gets astronomy data (structural anti-contamination).
    """
    # generalist repositories (Zenodo/Figshare/Dryad) serve ANY domain
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
    if _domain_ok("nea", domain):
        nea = _resolve_nea(text)
        if nea:
            return nea
    if _domain_ok("chembl", domain):
        cb = _resolve_chembl(text, opener=opener)
        if cb:
            return cb
    if _domain_ok("tdc", domain):
        td = _resolve_tdc(text)
        if td:
            return td
    if _domain_ok("pubchem", domain):
        pc = _resolve_pubchem(text)
        if pc:
            return pc
    m = _GEO_RE.search(text or "") if _domain_ok("geo", domain) else None
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
                     want_data: bool = False, domain: str = "",
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
            if _host_domain_ok(url, domain):
                _add(spec)                   # already a direct fetchable file URL
            continue
        ref = acc or url or str(spec.get("what") or "")
        resolved = resolve_reference(ref, verify=verify, want_data=want_data,
                                     domain=domain, opener=opener)
        if resolved:
            human = str(spec.get("what") or "")
            for i, r in enumerate(resolved):
                # keep the human description on the primary (series-matrix) spec
                _add({**r, "what": (human if i == 0 and human else r["what"])})
        elif url.lower().startswith("https://") and _host_domain_ok(url, domain):
            _add(spec)
    if not out:                              # mine the outline for an accession
        for r in resolve_reference(str(plan.get("analysis_outline") or ""),
                                   verify=verify, want_data=want_data,
                                   domain=domain, opener=opener):
            _add(r)
    return {**plan, "data_urls": out}
