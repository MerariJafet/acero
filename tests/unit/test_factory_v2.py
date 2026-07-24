"""C6: factory upgrades — re-plan, cache, cross-check, figures, snowballing."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal.experiment_factory import _compare_results, fetch_data, run_generated
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow

EXP = {"id": "exp_v2", "title": "t", "what": "w", "how": "h",
       "data_source": "s", "controls": "c", "discriminator": "d",
       "method_type": "simulation"}
HYP = {"title": "hipótesis"}


def _script(verdict, m=1.0):
    return f"""
import json
print("RESULT_JSON: " + json.dumps({{
    "metrics": {{"m": {m}, "n": 10}},
    "null_test": {{"description": "d", "statistic": 1.0, "threshold": 2.0,
                   "passed": True}},
    "verdict": "{verdict}", "verdict_reason": "razón"}}))
"""


def test_replan_with_alternative_dataset_on_fetch_failure():
    plans = {"n": 0}

    def plan(exp, hyp, domain, feedback=None):
        plans["n"] += 1
        if plans["n"] == 1:
            return {"data_urls": [{"url": "https://sidc.be/rota.csv",
                                   "filename": "a.csv", "what": ""}],
                    "analysis_outline": "x"}
        assert feedback and "FALLARON" in feedback     # got the failure context
        return {"data_urls": [], "analysis_outline": "autocontenido"}

    def bad_fetch(urls, dest, **k):
        raise ValueError("404 simulado")

    out = run_generated(EXP, HYP, plan=plan, fetch=bad_fetch,
                        codegen=lambda *a, **k: _script("refutes"),
                        verify_supports=False)
    assert out["ok"] is True and plans["n"] == 2       # re-planned and succeeded


def test_supports_cross_checked_and_agreeing_stays_supports():
    calls = {"n": 0}

    def cg(exp, hyp, files, previews, feedback=None):
        calls["n"] += 1
        if calls["n"] > 1:
            assert feedback and "INDEPENDIENTE" in feedback
        return _script("supports", m=1.0 if calls["n"] == 1 else 1.05)

    out = run_generated(EXP, HYP,
                        plan=lambda e, h, d, **k: {"data_urls": [],
                                                   "analysis_outline": "x"},
                        codegen=cg)
    assert out["ok"] is True
    assert out["result"]["verdict"] == "supports"      # 5% apart → within tolerance
    assert out["cross_check"]["agreed"] is True
    assert calls["n"] == 2                             # second implementation ran


def test_supports_degraded_when_implementations_disagree():
    calls = {"n": 0}

    def cg(exp, hyp, files, previews, feedback=None):
        calls["n"] += 1
        return _script("supports", m=1.0 if calls["n"] == 1 else 3.0)  # 3x apart

    out = run_generated(EXP, HYP,
                        plan=lambda e, h, d, **k: {"data_urls": [],
                                                   "analysis_outline": "x"},
                        codegen=cg)
    assert out["result"]["verdict"] == "inconclusive"
    assert "verificación cruzada" in out["result"]["verdict_reason"]
    assert out["cross_check"]["agreed"] is False


def test_refutes_needs_no_cross_check():
    calls = {"n": 0}

    def cg(*a, **k):
        calls["n"] += 1
        return _script("refutes")

    out = run_generated(EXP, HYP,
                        plan=lambda e, h, d, **k: {"data_urls": [],
                                                   "analysis_outline": "x"},
                        codegen=cg)
    assert out["result"]["verdict"] == "refutes" and calls["n"] == 1
    assert out["cross_check"] is None


def test_compare_results_tolerance():
    a = {"verdict": "supports", "metrics": {"x": 100.0}}
    assert _compare_results(a, {"verdict": "supports", "metrics": {"x": 110.0}})[0]
    assert not _compare_results(a, {"verdict": "supports", "metrics": {"x": 140.0}})[0]
    assert not _compare_results(a, {"verdict": "refutes", "metrics": {"x": 100.0}})[0]
    assert not _compare_results(a, {"verdict": "supports", "metrics": {"y": 1.0}})[0]


def test_fetch_cache_reuses_bytes(tmp_path, monkeypatch):
    served = {"n": 0}

    class FakeResp:
        def __init__(self):
            self.done = False

        def read(self, sz):
            if self.done:
                return b""
            self.done = True
            served["n"] += 1
            return b"col_a,col_b\n1,2\n"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import urllib.request as rq
    monkeypatch.setattr(rq, "urlopen", lambda req, timeout=0: FakeResp())
    urls = [{"url": "https://www.sidc.be/x.csv", "filename": "x.csv", "what": ""}]
    p1 = fetch_data(urls, tmp_path / "d1", cache_dir=tmp_path / "cache")
    p2 = fetch_data(urls, tmp_path / "d2", cache_dir=tmp_path / "cache")
    assert served["n"] == 1                            # network hit only once
    assert p1[0]["cached"] is False and p2[0]["cached"] is True
    assert p1[0]["sha256"] == p2[0]["sha256"]


def test_figures_collected(tmp_path):
    script = """
import json, os
os.makedirs("out", exist_ok=True)
open("out/fig1.png", "wb").write(b"png")
print("RESULT_JSON: " + json.dumps({
    "metrics": {"m": 1.0},
    "null_test": {"description": "d", "statistic": 1, "threshold": 2, "passed": True},
    "verdict": "refutes", "verdict_reason": "r"}))
"""
    out = run_generated(dict(EXP, id="exp_fig"), HYP,
                        plan=lambda e, h, d, **k: {"data_urls": [],
                                                   "analysis_outline": "x"},
                        codegen=lambda *a, **k: script, verify_supports=False)
    assert out["result"]["figures"] == ["fig1.png"]


def test_deepen_literature_snowballs_references(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Deep", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    fl.store.put(p.id, "literature", "lit_seed",
                 {"id": "lit_seed", "hyp_id": h["id"], "title": "Semilla",
                  "doi": "10.1/seed", "referenced_works": ["W1", "W2"],
                  "url": "https://doi.org/10.1/seed"},
                 status="INDEXED", actor="t", summary="s")

    def fake_snowball(ids, rows=10):
        assert ids == ["W1", "W2"]
        return [{"title": "Referencia Uno", "doi": "10.1/r1", "type": "article",
                 "integrity": "ok", "url": "https://doi.org/10.1/r1",
                 "authors": [], "abstract": "abs", "topics": [],
                 "source": "openalex", "relevance": None,
                 "openalex_id": "W1", "referenced_works": []},
                {"title": "Semilla", "doi": "10.1/seed", "type": "article",
                 "integrity": "ok", "url": "", "authors": [], "abstract": "",
                 "topics": [], "source": "openalex", "relevance": None,
                 "openalex_id": "W2", "referenced_works": []}]

    out = fl.deepen_literature(p.id, h["id"], snowballer=fake_snowball,
                               pdf_fetcher=lambda aid: b"nope")
    assert out["ok"] is True
    assert out["level2_added"] == 1                    # seed itself deduped
    lits = fl.store.list_objects(p.id, kind="literature")
    l2 = [x for x in lits if x.get("depth") == 2]
    assert len(l2) == 1 and l2[0]["title"] == "Referencia Uno"


def test_deepen_requires_prior_investigation(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Deep2", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    out = fl.deepen_literature(p.id, h["id"], snowballer=lambda *a, **k: [])
    assert out["ok"] is False and "investiga primero" in out["error"]


def test_download_deadline_kills_runaway(tmp_path, monkeypatch):
    """A slow/unbounded download must abort at the wall-clock budget, not hang."""
    import acero.portal.experiment_factory as fx
    monkeypatch.setattr(fx, "DOWNLOAD_DEADLINE_SEC", 0)  # trip immediately

    class SlowResp:
        def read(self, n):
            return b"x" * 1024          # always returns data → would never end
        def __enter__(self): return self
        def __exit__(self, *a): return False
    import urllib.request as rq
    monkeypatch.setattr(rq, "urlopen", lambda req, timeout=0: SlowResp())
    import pytest
    with pytest.raises(ValueError, match="presupuesto"):
        fx.fetch_data([{"url": "https://www.sidc.be/x.csv", "filename": "x.csv",
                        "what": ""}], tmp_path, cache_dir=tmp_path / "c")
