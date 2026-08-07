"""Novelty check (anti-Erdősgate) — literature search + judge, offline."""
from __future__ import annotations

from acero.discovery.novelty_check import NoveltyChecker, _reconstruct_abstract


class _Prov:
    def __init__(self, out):
        self.out = out

    def available(self):
        return True

    def complete_json(self, prompt, schema, *, temperature=0.0):
        return self.out


HITS = [{"title": "A proof of two Erdős conjectures", "doi": "10.x/1", "year": 2003,
         "abstract": "we prove the conjecture on restricted addition"}]


def test_already_resolved_when_a_paper_solves_it():
    prov = _Prov({"verdict": "already_resolved", "recovery_risk": 0.95,
                  "resolving_papers": [{"title": "A proof…", "doi": "10.x/1",
                                        "why": "prueba directa de la afirmación"}],
                  "rationale": "publicado en 2003", "recommendation": "no correr; es recuperación"})
    r = NoveltyChecker(provider=prov, searcher=lambda q, k: HITS).check("Erdős #339")
    assert r["verdict"] == "already_resolved" and r["recovery_risk"] > 0.9
    assert r["resolving_papers"][0]["doi"] == "10.x/1"


def test_likely_open_never_says_novel():
    prov = _Prov({"verdict": "likely_open", "recovery_risk": 0.3, "resolving_papers": [],
                  "rationale": "nada lo resuelve", "recommendation": "correr con cautela"})
    r = NoveltyChecker(provider=prov, searcher=lambda q, k: HITS).check("algo nuevo")
    assert r["verdict"] == "likely_open"           # el techo, nunca 'novel'
    assert r["verdict"] != "novel"


def test_no_search_results_is_uncertain_not_green_light():
    r = NoveltyChecker(provider=_Prov({}), searcher=lambda q, k: []).check("x")
    assert r["verdict"] == "uncertain" and r["searched"] is False
    assert 0.4 <= r["recovery_risk"] <= 0.6         # honest ignorance, no green light


def test_hits_but_no_ai_judge_stays_uncertain():
    class _Down:
        def available(self):
            return False
    r = NoveltyChecker(provider=_Down(), searcher=lambda q, k: HITS).check("x")
    assert r["verdict"] == "uncertain" and r["hits"] == HITS


def test_abstract_reconstruction_from_inverted_index():
    inv = {"we": [0], "prove": [1], "it": [2]}
    assert _reconstruct_abstract(inv) == "we prove it"
    assert _reconstruct_abstract(None) == ""


def test_multi_query_search_dedups_across_queries():
    calls = []

    def searcher(q, k):
        calls.append(q)
        return [{"title": "Same paper", "doi": "10.1/x", "year": 2020,
                 "abstract": "a", "source": "openalex"}]

    prov = _Prov({"verdict": "likely_open", "recovery_risk": 0.3, "confidence": 0.6,
                  "resolving_papers": [], "related_papers": [], "rationale": "r",
                  "recommendation": "c"})
    nc = NoveltyChecker(provider=prov, searcher=searcher, query_gen=lambda c: ["q1", "q2"])
    r = nc.check("claim")
    assert r["queries"] == ["q1", "q2"]
    assert len(calls) == 2                 # both crafted queries were searched
    assert len(r["hits"]) == 1             # same paper deduped across queries


def test_resolving_paper_forces_already_resolved_even_if_judge_hedged():
    prov = _Prov({"verdict": "likely_open",           # judge hedged...
                  "recovery_risk": 0.8, "confidence": 0.7,
                  "resolving_papers": [{"title": "T", "doi": "10/2", "why": "resuelve"}],
                  "related_papers": [], "rationale": "r", "recommendation": "c"})
    r = NoveltyChecker(provider=prov, searcher=lambda q, k: HITS,
                       query_gen=lambda c: ["q"]).check("x")
    assert r["verdict"] == "already_resolved"          # ...a concrete resolver is decisive


def test_sources_and_queries_are_reported():
    hits = [{"title": "P", "doi": "10/9", "year": 2019, "abstract": "a", "source": "arxiv"}]
    prov = _Prov({"verdict": "likely_open", "recovery_risk": 0.3, "confidence": 0.5,
                  "resolving_papers": [], "related_papers": [], "rationale": "r",
                  "recommendation": "c"})
    r = NoveltyChecker(provider=prov, searcher=lambda q, k: hits,
                       query_gen=lambda c: ["q"]).check("x")
    assert r["sources"] == ["arxiv"] and r["queries"] == ["q"]
