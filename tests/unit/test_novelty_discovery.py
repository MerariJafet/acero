"""Discovery orientation: novelty filter + discovery angles + cross-catalog (offline)."""

from __future__ import annotations

from acero.ledger.service import ResearchLedger
from acero.portal import data_resolver as dr
from acero.portal.hypotheses import HypothesisService
from acero.portal.novelty import NoveltyFilter


def _setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Descubrir", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    return p, h


def test_novelty_offline_is_honest(session_factory):
    p, h = _setup(session_factory)
    out = NoveltyFilter(session_factory).assess(p.id, h["id"], use_ai=False)
    assert out["ok"] is True
    assert out["status"] == "sin_evaluar" and out["score"] is None  # no fake novelty
    stored = HypothesisService(session_factory).store.get(h["id"])
    assert stored["novelty"]["status"] == "sin_evaluar"


def test_assess_all_skips_already_assessed(session_factory):
    p, h = _setup(session_factory)
    nf = NoveltyFilter(session_factory)
    nf.store.update_payload(h["id"], {"novelty": {"status": "abierta", "score": 7.5}})
    out = nf.assess_all(p.id, use_ai=False)
    assert all(a["tag"] != h["tag"] for a in out["assessed"])  # not re-assessed


def test_generation_stores_discovery_angle(session_factory):
    # deterministic generation still yields hypotheses; AI path adds discovery_angle
    p, h = _setup(session_factory)
    assert "discovery_angle" in h  # field present (may be empty in deterministic)


def test_stellarhosts_resolver_for_chemistry_crossmatch():
    specs = dr.resolve_reference(
        "cruzar radios de exoplanetas con abundancias/química estelar por hostname")
    urls = " ".join(s["url"] for s in specs)
    assert "pscomppars" in urls          # planet radii
    assert "stellarhosts" in urls        # stellar params to cross-match
    assert any(s["accession"] == "stellarhosts" for s in specs)


def test_chemistry_alone_offers_stellar_catalog():
    specs = dr.resolve_reference("catálogo de abundancias estelares Hypatia")
    assert specs and any(s["accession"] == "stellarhosts" for s in specs)
