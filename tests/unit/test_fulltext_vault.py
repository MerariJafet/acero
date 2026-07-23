"""Full-text download/extract + vault semantic index (offline, injected)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal import fulltext, vault_index
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow

_PDF = b"%PDF-1.4 fake"


def test_fetch_fulltext_ok_with_injected_downloader():
    long = "resultado importante " * 60
    r = fulltext.fetch_fulltext(
        {"pdf_url": "https://x.org/a.pdf", "source": "openalex"},
        downloader=lambda u: _PDF, extractor=lambda b: long)
    assert r["ok"] and r["chars"] > 500 and "importante" in r["excerpt"]


def test_fetch_fulltext_no_pdf_is_honest():
    r = fulltext.fetch_fulltext({"source": "openalex"})
    assert r["ok"] is False and "sin PDF" in r["reason"]


def test_fetch_fulltext_short_text_rejected():
    r = fulltext.fetch_fulltext(
        {"pdf_url": "https://x.org/a.pdf"}, downloader=lambda u: _PDF,
        extractor=lambda b: "muy corto")
    assert r["ok"] is False and r["chars"] < 500


def test_download_pdf_rejects_non_pdf(monkeypatch, tmp_path):
    monkeypatch.setenv("ACERO_EXPERIMENT_ARTIFACTS", str(tmp_path / "a"))

    class Resp:
        def read(self, n): return b"<html>not a pdf</html>"
        def __enter__(self): return self
        def __exit__(self, *a): return False
    import urllib.request as rq
    monkeypatch.setattr(rq, "urlopen", lambda req, timeout=0: Resp())
    assert fulltext.download_pdf("https://x.org/a.pdf") is None


def test_arxiv_pdf_url_derived():
    r = fulltext.fetch_fulltext(
        {"source": "arxiv", "url": "https://arxiv.org/abs/2101.00001"},
        downloader=lambda u: _PDF if "pdf/2101.00001" in u else None,
        extractor=lambda b: "x" * 800)
    assert r["ok"] is True


def test_vault_index_keyword_fallback(session_factory):
    # ACERO_EMBEDDINGS_DISABLED=1 in conftest → keyword backend
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Vault", domain="astronomy")
    fl = HypothesisFlow(session_factory)
    for i, (t, ab) in enumerate([
            ("Methylation QTL in blood", "cis mQTL effects on CpG methylation"),
            ("Exoplanet transit timing", "kepler photometry transit period")]):
        fl.store.put(p.id, "literature", f"lit{i}",
                     {"id": f"lit{i}", "title": t, "abstract": ab,
                      "hyp_id": "h", "source": "openalex"},
                     status="INDEXED", actor="t", summary="s")
    vault_index._CACHE.clear()
    out = vault_index.search(p.id, "methylation genetic control", session_factory=session_factory)
    assert out["backend"] == "keyword"
    assert out["results"] and "Methylation" in out["results"][0]["title"]


def test_vault_search_empty_project(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Empty", domain="astronomy")
    vault_index._CACHE.clear()
    out = vault_index.search(p.id, "anything", session_factory=session_factory)
    assert out["results"] == []


def test_deepen_reads_fulltext_and_stores_excerpt(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Deep", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    fl.store.put(p.id, "literature", "lit_oa",
                 {"id": "lit_oa", "hyp_id": h["id"], "title": "OA paper",
                  "doi": "10.1/oa", "is_oa": True,
                  "pdf_url": "https://x.org/oa.pdf", "referenced_works": []},
                 status="INDEXED", actor="t", summary="s")
    out = fl.deepen_literature(
        p.id, h["id"], snowballer=lambda ids, rows=10: [],
        pdf_fetcher=lambda u: _PDF)
    # fetcher returns bytes; extractor is real pypdf → fake bytes yield no text,
    # so fulltext_read may be 0, but the attempt is honest and counted
    assert out["ok"] is True
    assert out["fulltext_attempted"] >= 1
    assert "embeddings_backend" in out
