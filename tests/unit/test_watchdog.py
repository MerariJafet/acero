"""C4: literature watchdog — push diffing with injected searcher (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.watchdog import Watchdog, _keys

P1 = {"title": "Paper Uno", "doi": "10.1/uno", "type": "article", "integrity": "ok",
      "url": "https://doi.org/10.1/uno", "authors": ["A"], "abstract": "abs uno",
      "topics": [], "source": "openalex", "relevance": 9.0}
P2 = {"title": "Paper Dos", "doi": "10.1/dos", "type": "article", "integrity": "ok",
      "url": "https://doi.org/10.1/dos", "authors": ["B"], "abstract": "abs dos",
      "topics": [], "source": "arxiv", "relevance": 5.0}


def _setup(session_factory, with_query=True):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Watch", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    if with_query:
        fl.store.update_payload(h["id"], {
            "confrontation": {"query_used": "cmb anomaly test"}})
    return p, h, fl


def test_scan_indexes_only_new_papers(session_factory):
    p, h, fl = _setup(session_factory)
    # P1 already known to the project
    fl.store.put(p.id, "literature", "lit_known",
                 {"id": "lit_known", "title": "Paper Uno", "doi": "10.1/uno"},
                 status="INDEXED", actor="t", summary="k")
    wd = Watchdog(session_factory)
    out = wd.scan_project(p.id, searcher=lambda q, domain="", rows=6: [P1, P2],
                          use_ai=False)
    assert out["ok"] is True and out["total_new"] == 1
    lits = fl.store.list_objects(p.id, kind="literature")
    fresh = [x for x in lits if x.get("new_evidence")]
    assert len(fresh) == 1 and fresh[0]["title"] == "Paper Dos"
    assert fresh[0]["abstract"] == "abs dos"          # abstract preserved
    # hypothesis flagged for the UI
    assert fl.store.get(h["id"])["new_evidence_count"] == 1


def test_second_scan_finds_nothing_new(session_factory):
    p, h, fl = _setup(session_factory)
    wd = Watchdog(session_factory)
    s = lambda q, domain="", rows=6: [P1, P2]  # noqa: E731
    o1 = wd.scan_project(p.id, searcher=s, use_ai=False)
    o2 = wd.scan_project(p.id, searcher=s, use_ai=False)
    assert o1["total_new"] == 2 and o2["total_new"] == 0


def test_scan_skips_uninvestigated_hypotheses(session_factory):
    p, h, fl = _setup(session_factory, with_query=False)
    wd = Watchdog(session_factory)
    out = wd.scan_project(p.id, searcher=lambda *a, **k: [P1], use_ai=False)
    assert out["total_new"] == 0 and out["by_hyp"] == []


def test_searcher_error_is_isolated(session_factory):
    p, h, fl = _setup(session_factory)

    def boom(q, domain="", rows=6):
        raise RuntimeError("api caída")
    out = Watchdog(session_factory).scan_project(p.id, searcher=boom, use_ai=False)
    assert out["ok"] is True                          # scan survives
    assert out["by_hyp"][0]["error"].startswith("api caída")


def test_last_scan_recorded(session_factory):
    p, h, fl = _setup(session_factory)
    wd = Watchdog(session_factory)
    assert wd.last_scan(p.id) is None
    wd.scan_project(p.id, searcher=lambda *a, **k: [], use_ai=False)
    last = wd.last_scan(p.id)
    assert last is not None and last["total_new"] == 0


def test_keys_dedup_by_doi_and_title():
    ks = _keys([{"doi": "10.1/X", "title": "Algo Grande"}])
    assert "doi:10.1/x" in ks and any(k.startswith("t:algo grande") for k in ks)
