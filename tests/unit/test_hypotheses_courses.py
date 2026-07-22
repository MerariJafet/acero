"""Critical hypothesis generation + course deletion (offline/deterministic)."""

from __future__ import annotations

import pytest

from acero.discovery.store import DiscoveryStore
from acero.ledger.service import ResearchLedger
from acero.portal.education import EducationService
from acero.portal.hypotheses import HypothesisService


@pytest.fixture()
def proj(session_factory):
    lg = ResearchLedger(session_factory)
    return lg.create_project("Place test", domain="astronomy")


def test_hypotheses_have_critical_reasoning_fields(session_factory, proj):
    hs = HypothesisService(session_factory)
    r = hs.generate(proj.id, use_ai=False)
    assert r["ok"] and r["created"]
    h = r["created"][0]
    for field in ("kind", "trigger_question", "argument", "doubt", "test_idea",
                  "competes_with"):
        assert field in h
    # spans multiple hypothesis kinds (not just one)
    kinds = {x["kind"] for x in r["created"]}
    assert kinds & {"established", "theorized", "novel", "open_question"}


def test_hypotheses_are_candidates_not_discoveries(session_factory, proj):
    hs = HypothesisService(session_factory)
    r = hs.generate(proj.id, use_ai=False)
    assert "no son" in r["disclaimer"].lower() or "candidatos" in r["disclaimer"].lower()
    store = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    saved = store.list_objects(proj.id, kind="candidate")
    assert saved and all(s["status"] == "PROPOSED" for s in saved)


def test_delete_course(session_factory, proj):
    edu = EducationService(session_factory)
    edu.build_edu_plan(proj.id, use_ai=False)
    c = edu.generate_course(proj.id, use_ai=False)["course"]
    assert len(edu.list_courses(proj.id)) == 1
    out = edu.delete_course(c["id"])
    assert out["ok"] is True
    assert len(edu.list_courses(proj.id)) == 0


def test_delete_missing_course_is_graceful(session_factory):
    out = EducationService(session_factory).delete_course("course_nope")
    assert out["ok"] is False
