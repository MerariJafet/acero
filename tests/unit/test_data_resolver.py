"""Data resolver: accessions → real download URLs (offline, no network)."""

from __future__ import annotations

from acero.portal import data_resolver as dr


def test_geo_series_matrix_url_pattern():
    u = dr._geo_series_matrix_url("GSE111629")
    assert u == ("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE111nnn/"
                 "GSE111629/matrix/GSE111629_series_matrix.txt.gz")
    # short accession
    assert "GSE1nnn/GSE1234/" in dr._geo_series_matrix_url("GSE1234")


def test_resolve_reference_finds_geo_in_text():
    r = dr.resolve_reference("bajar de GEO GSE55763 en sangre", verify=False)
    assert len(r) == 1 and r[0]["accession"] == "GSE55763"
    assert r[0]["repository"] == "GEO"
    assert r[0]["url"].endswith("GSE55763_series_matrix.txt.gz")


def test_resolve_reference_none_when_no_accession():
    assert dr.resolve_reference("un dataset genérico sin ID", verify=False) == []


def test_geo_supplementary_files_parsed(monkeypatch):
    html = ('<a href="GSE111629_PEGblood_450kMethylationDataBackgroundNormalized.txt.gz">x</a>'
            '<a href="GSE111629_RAW.tar">raw</a>'
            '<a href="filelist.txt">list</a>')

    class Resp:
        def read(self): return html.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    files = dr.geo_supplementary_files("GSE111629", opener=lambda req, timeout=0: Resp())
    # RAW.tar and filelist skipped; the normalized methylation matrix is first + is_data
    names = [f["filename"] for f in files]
    assert "GSE111629_RAW.tar" not in names and "filelist.txt" not in names
    assert files[0]["is_data"] and "Normalized" in files[0]["filename"]


def test_want_data_adds_supplementary_matrix(monkeypatch):
    html = '<a href="GSE1_processed_beta_matrix.txt.gz">m</a>'

    class Resp:
        def read(self): return html.encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    specs = dr.resolve_reference("GEO GSE123", verify=False, want_data=True,
                                 opener=lambda req, timeout=0: Resp())
    # series matrix (metadata) + supplementary data matrix (betas)
    assert len(specs) == 2
    assert any("series_matrix" in s["url"] for s in specs)
    assert any("processed_beta_matrix" in s["url"] for s in specs)


def test_enrich_plan_fills_url_from_accession():
    plan = {"data_urls": [{"url": "", "accession": "GSE111629",
                           "filename": "", "what": "metilación"}],
            "analysis_outline": "x"}
    out = dr.enrich_plan_urls(plan, verify=False)
    assert out["data_urls"][0]["url"].endswith("GSE111629_series_matrix.txt.gz")
    assert out["data_urls"][0]["what"] == "metilación"     # keeps human description


def test_enrich_keeps_direct_https_urls():
    plan = {"data_urls": [{"url": "https://www.sidc.be/x.csv", "accession": "",
                           "filename": "x.csv", "what": "sunspots"}],
            "analysis_outline": "y"}
    out = dr.enrich_plan_urls(plan, verify=False)
    assert out["data_urls"][0]["url"] == "https://www.sidc.be/x.csv"


def test_enrich_mines_outline_when_no_urls():
    plan = {"data_urls": [], "analysis_outline": "usar GSE42861 de GEO"}
    out = dr.enrich_plan_urls(plan, verify=False)
    assert out["data_urls"] and out["data_urls"][0]["accession"] == "GSE42861"


def test_enrich_dedups():
    plan = {"data_urls": [
        {"url": "", "accession": "GSE111629", "filename": "", "what": "a"},
        {"url": "", "accession": "GSE111629", "filename": "", "what": "b"}],
        "analysis_outline": ""}
    out = dr.enrich_plan_urls(plan, verify=False)
    assert len(out["data_urls"]) == 1


def test_gunzip_roundtrip(tmp_path):
    import gzip

    from acero.portal.experiment_factory import _gunzip
    gz = tmp_path / "data.txt.gz"
    with gzip.open(gz, "wb") as f:
        f.write(b"col_a,col_b\n1,2\n3,4\n")
    name = _gunzip(gz)
    assert name == "data.txt"
    assert (tmp_path / "data.txt").read_text() == "col_a,col_b\n1,2\n3,4\n"


def test_nea_resolver_builds_tap_urls():
    specs = dr.resolve_reference("Kepler DR25 KOI del NASA Exoplanet Archive, radius valley")
    repos = {s["repository"] for s in specs}
    assert repos == {"NASA-NEA"}
    assert any("q1_q17_dr25_koi" in s["url"] for s in specs)
    assert any("pscomppars" in s["url"] for s in specs)
    assert all(s["url"].startswith("https://exoplanetarchive.ipac.caltech.edu/TAP")
               and "format=csv" in s["url"] for s in specs)


def test_nea_confirmed_planets_reference():
    specs = dr.resolve_reference("usar confirmed planets del exoplanet archive")
    assert specs and specs[0]["accession"] == "pscomppars"


def test_figshare_resolver(monkeypatch):
    import json as _j

    class Resp:
        def read(self):
            return _j.dumps({"files": [
                {"name": "data_processed.csv",
                 "download_url": "https://ndownloader.figshare.com/files/999", "size": 50},
                {"name": "photo.png", "download_url": "https://x/p.png"}]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    specs = dr.figshare_files("1234567", opener=lambda req, timeout=0: Resp())
    names = [s["filename"] for s in specs]
    assert "data_processed.csv" in names and "photo.png" not in names
    assert specs[0]["repository"] == "Figshare"


def test_dryad_resolver(monkeypatch):
    import json as _j

    class Resp:
        def read(self):
            return _j.dumps({"_links": {"stash:download": {
                "href": "/api/v2/datasets/doi%3A10.5061%2Fdryad.abc/download"}}}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    specs = dr.dryad_download("abc123", opener=lambda req, timeout=0: Resp())
    assert specs and specs[0]["repository"] == "Dryad"
    assert specs[0]["url"].startswith("https://datadryad.org/api/v2/datasets/")
    assert specs[0]["filename"].endswith(".zip")


def test_resolve_reference_routes_figshare_and_dryad(monkeypatch):
    import json as _j

    class FRsp:
        def read(self):
            return _j.dumps({"files": [{"name": "d.csv",
                "download_url": "https://ndownloader.figshare.com/files/1", "size": 1}]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(dr.urllib.request, "urlopen", lambda req, timeout=0: FRsp())
    assert dr.resolve_reference("datos en 10.6084/m9.figshare.1234567")[0]["repository"] == "Figshare"


def test_nea_does_not_hijack_molecular_chemistry():
    # a DRUG chemistry experiment (Caco-2 permeability, lipophilicity) must NOT
    # pull NASA exoplanet data just because it mentions 'chemical/elemental'
    specs = dr.resolve_reference(
        "correlación estructura-propiedad: permeabilidad Caco-2 vs lipofilicidad "
        "y rigidez molecular en compuestos químicos, PubChem")
    accs = {s.get("accession") for s in specs}
    assert "pscomppars" not in accs and "stellarhosts" not in accs


def test_nea_still_fires_for_stellar_chemistry():
    specs = dr.resolve_reference(
        "cruzar radios de exoplanetas con abundancias de química estelar (host star)")
    accs = {s.get("accession") for s in specs}
    assert "pscomppars" in accs and "stellarhosts" in accs
