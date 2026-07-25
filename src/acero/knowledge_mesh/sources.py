"""Scientific Source Registry — VERIFIED seed sources (Phase 1).

Every source here was verified with a REAL HTTP request (see health_check). No
source is invented. Health status/HTTP code are recorded from live probes; call
``health_check_all`` to refresh them. Sources that fail verification are kept and
marked, never silently dropped.
"""

from __future__ import annotations

from typing import Any

from .models import AuthorityLevel, HealthStatus, SourceRecord

_UA = "ACERO-knowledge-mesh/0.1 (+https://github.com/MerariJafet/acero)"

# Seed registry. Domains/licenses from each provider's official documentation.
SEED_SOURCES: list[SourceRecord] = [
    SourceRecord(
        source_id="crossref", name="Crossref REST API",
        canonical_domain="api.crossref.org", responsible_institution="Crossref",
        scientific_domains=["all"], source_types=["PEER_REVIEWED_ARTICLE", "PREPRINT", "DATASET"],
        authority_level=AuthorityLevel.OFFICIAL_AGGREGATOR,
        documentation_url="https://api.crossref.org/swagger-ui/index.html",
        api_base_url="https://api.crossref.org",
        health_check_url="https://api.crossref.org/works/10.1038/nphys1170",
        metadata_license="CC0 (Crossref metadata)", file_license_model="varies (publisher)",
        commercial_use="allowed", bulk_access="polite pool + metadata plus dumps",
        connector_status="tested",
        notes=["exposes license, funding, corrections/retractions (Crossmark)"]),
    SourceRecord(
        source_id="openalex", name="OpenAlex API",
        canonical_domain="api.openalex.org", responsible_institution="OurResearch",
        scientific_domains=["all"], source_types=["PEER_REVIEWED_ARTICLE", "PREPRINT"],
        authority_level=AuthorityLevel.OFFICIAL_AGGREGATOR,
        documentation_url="https://docs.openalex.org",
        api_base_url="https://api.openalex.org",
        health_check_url="https://api.openalex.org/works?per-page=1",
        metadata_license="CC0", commercial_use="allowed",
        bulk_access="snapshot on AWS S3", connector_status="prototype"),
    SourceRecord(
        source_id="arxiv", name="arXiv API",
        canonical_domain="export.arxiv.org", responsible_institution="Cornell University / arXiv",
        scientific_domains=["physics", "astronomy", "math", "cs", "quant-ph"],
        source_types=["PREPRINT"], authority_level=AuthorityLevel.PRIMARY,
        documentation_url="https://info.arxiv.org/help/api/index.html",
        api_base_url="https://export.arxiv.org/api",
        health_check_url="https://export.arxiv.org/api/query?search_query=all:electron&max_results=1",
        metadata_license="arXiv metadata terms", file_license_model="per-submission license",
        bulk_access="bulk data via S3 requester-pays (not enabled)", connector_status="prototype"),
    SourceRecord(
        source_id="nasa_mast", name="MAST (Mikulski Archive for Space Telescopes)",
        canonical_domain="mast.stsci.edu", responsible_institution="STScI / NASA",
        scientific_domains=["astronomy", "astrophysics"],
        source_types=["OBSERVATION", "DATASET"], authority_level=AuthorityLevel.PRIMARY,
        documentation_url="https://mast.stsci.edu/api/v0/",
        api_base_url="https://mast.stsci.edu/api/v0", health_check_url="https://mast.stsci.edu/api/v0/",
        metadata_license="public domain (NASA)", file_license_model="public domain",
        commercial_use="allowed", connector_status="prototype",
        notes=["ACERO already downloads Kepler light curves from the MAST archive"]),
    SourceRecord(
        source_id="gwosc", name="GWOSC (Gravitational Wave Open Science Center)",
        canonical_domain="gwosc.org", responsible_institution="LIGO/Virgo/KAGRA",
        scientific_domains=["gravitational waves", "astrophysics"],
        source_types=["OBSERVATION", "DATASET"], authority_level=AuthorityLevel.PRIMARY,
        documentation_url="https://gwosc.org/apidocs/",
        api_base_url="https://gwosc.org", health_check_url="https://gwosc.org/eventapi/json/",
        metadata_license="open", file_license_model="open (CC)", connector_status="prototype"),
    SourceRecord(
        source_id="ncbi_eutils", name="NCBI E-utilities",
        canonical_domain="eutils.ncbi.nlm.nih.gov", responsible_institution="NCBI / NIH",
        scientific_domains=["genetics", "genomics", "biology", "medicine"],
        source_types=["DATASET", "PEER_REVIEWED_ARTICLE"], authority_level=AuthorityLevel.PRIMARY,
        documentation_url="https://www.ncbi.nlm.nih.gov/books/NBK25501/",
        api_base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        health_check_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?retmode=json",
        metadata_license="US Gov public domain (most)", personal_data_risk="high",
        connector_status="prototype",
        notes=["controlled-access human data must NOT be ingested without authorization"]),
    SourceRecord(
        source_id="pubchem", name="PubChem PUG REST",
        canonical_domain="pubchem.ncbi.nlm.nih.gov", responsible_institution="NCBI / NIH",
        scientific_domains=["chemistry"], source_types=["DATASET"],
        authority_level=AuthorityLevel.PRIMARY,
        documentation_url="https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
        api_base_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        health_check_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/cids/JSON",
        metadata_license="public domain (most)", connector_status="prototype"),
    SourceRecord(
        source_id="zenodo", name="Zenodo REST API",
        canonical_domain="zenodo.org", responsible_institution="CERN / OpenAIRE",
        scientific_domains=["all"], source_types=["DATASET", "SOFTWARE", "PREPRINT"],
        authority_level=AuthorityLevel.OFFICIAL_AGGREGATOR,
        documentation_url="https://developers.zenodo.org/",
        api_base_url="https://zenodo.org/api", health_check_url="https://zenodo.org/api/records?size=1",
        metadata_license="metadata often CC0; FILE license varies per record",
        file_license_model="varies per record — evaluate individually",
        bulk_access="OAI-PMH / dumps recommended for bulk", connector_status="prototype",
        notes=["metadata license != file license; check each record"]),
    SourceRecord(
        source_id="datacite", name="DataCite REST API",
        canonical_domain="api.datacite.org", responsible_institution="DataCite",
        scientific_domains=["all"], source_types=["DATASET"],
        authority_level=AuthorityLevel.OFFICIAL_AGGREGATOR,
        documentation_url="https://support.datacite.org/docs/api",
        api_base_url="https://api.datacite.org",
        health_check_url="https://api.datacite.org/heartbeat",
        metadata_license="CC0", connector_status="not_started",
        notes=["verified live at /heartbeat (an earlier probe URL timed out)"]),
]


def registry() -> list[SourceRecord]:
    return list(SEED_SOURCES)


def get_source(source_id: str) -> SourceRecord | None:
    return next((s for s in SEED_SOURCES if s.source_id == source_id), None)


def health_check(source: SourceRecord, *, timeout: float = 15.0) -> dict[str, Any]:
    """Do a REAL request to the source's health-check URL and record the result."""
    import urllib.error
    import urllib.request

    from ..core.clock import now_iso
    url = source.health_check_url or source.api_base_url
    status: int | None = None
    ok = False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = int(r.status)
            ok = 200 <= status < 400
    except urllib.error.HTTPError as e:
        status = int(e.code)
        ok = False
    except Exception:  # noqa: BLE001 - network/DNS/timeout
        status = None
        ok = False
    source.last_http_status = status
    source.last_health_check = now_iso()
    source.health_status = HealthStatus.ACTIVE if ok else (
        HealthStatus.PARTIAL if status else HealthStatus.UNKNOWN)
    return {"source_id": source.source_id, "http_status": status, "ok": ok,
            "health_status": source.health_status.value, "url": url}


def health_check_all(*, timeout: float = 15.0) -> dict[str, Any]:
    results = [health_check(s, timeout=timeout) for s in SEED_SOURCES]
    n_ok = sum(1 for r in results if r["ok"])
    return {"n_sources": len(results), "n_verified": n_ok, "results": results}
