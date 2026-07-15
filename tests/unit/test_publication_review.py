"""Sprint 12 tests: review dossier, human sign-off, gated local export."""

from __future__ import annotations

import pytest

from acero.publication.dossier import DossierEvidence
from acero.publication.engine import build_dossier
from acero.publication.export import (
    AI_USE_DECLARATION,
    ExportBlocked,
    evaluate_export,
    export_dossier,
)
from acero.publication.review import (
    HumanReviewSession,
    ReviewDecision,
    ReviewError,
)
from acero.reliability.scorecard import ReadinessLevel


def _ready_dossier(**kw):
    return build_dossier(
        "proj", "damped oscillation recovered", externally_validated=True,
        supporting=[DossierEvidence("e1", "clean recovery", "supporting"),
                    DossierEvidence("e2", "same run again", "supporting",
                                    independent_group="g1"),
                    DossierEvidence("e3", "third", "supporting", independent_group="g1")],
        counter=[DossierEvidence("c1", "noise degrades fit", "counter")],
        limitations=["computational only"], **kw)


def _approved_review(d, reviewer="Merari"):
    r = HumanReviewSession(dossier_id=d.id, reviewer=reviewer, comprehension_ok=True)
    for s in ("central_claim", "main_evidence", "main_counter_evidence", "limitations",
              "reliability", "what_remains_to_validate_externally"):
        r.acknowledge(s)
    r.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["reviewed; evidence and limitations understood"])
    return r


# --- dossier --------------------------------------------------------------

def test_dossier_states_what_it_is_not():
    disc = " ".join(_ready_dossier().disclaimers())
    assert "NOT a discovery" in disc and "NOT a publication" in disc
    assert "DISCOVERY_CONFIRMED" in disc


def test_dossier_independent_support_collapses_duplicates():
    d = _ready_dossier()
    # e2,e3 share group g1; e1 stands alone → 2 independent groups
    assert d.independent_support_count() == 2


def test_ready_dossier_reaches_review_ceiling():
    d = _ready_dossier()
    assert d.readiness == ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW.value


# --- review ---------------------------------------------------------------

def test_ai_reviewer_cannot_approve():
    d = _ready_dossier()
    ai = HumanReviewSession(dossier_id=d.id, reviewer="ACERO", comprehension_ok=True)
    for s in ("central_claim", "main_evidence", "main_counter_evidence", "limitations",
              "reliability", "what_remains_to_validate_externally"):
        ai.acknowledge(s)
    with pytest.raises(ReviewError):
        ai.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["reviewed; evidence and limitations understood"])


def test_approval_requires_all_acknowledgements():
    d = _ready_dossier()
    r = HumanReviewSession(dossier_id=d.id, reviewer="Merari", comprehension_ok=True)
    r.acknowledge("central_claim")
    with pytest.raises(ReviewError):
        r.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["reviewed; evidence and limitations understood"])


def test_approval_requires_comprehension():
    d = _ready_dossier()
    r = HumanReviewSession(dossier_id=d.id, reviewer="Merari", comprehension_ok=False)
    for s in ("central_claim", "main_evidence", "main_counter_evidence", "limitations",
              "reliability", "what_remains_to_validate_externally"):
        r.acknowledge(s)
    with pytest.raises(ReviewError):
        r.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["reviewed; evidence and limitations understood"])


def test_no_approve_for_publication_decision_exists():
    assert not any(d.name == "APPROVE_FOR_PUBLICATION" for d in ReviewDecision)


def test_request_changes_records_without_acknowledgements():
    d = _ready_dossier()
    r = HumanReviewSession(dossier_id=d.id, reviewer="Merari")
    r.record(ReviewDecision.REQUEST_CHANGES, dossier=d, reasons=["needs more evidence"])
    assert r.decision == ReviewDecision.REQUEST_CHANGES
    assert r.content_hash                       # a hash is recorded (anti-tamper)


# --- gated export ---------------------------------------------------------

def test_export_blocked_without_review():
    d = _ready_dossier()
    dec = evaluate_export(d, None)
    assert not dec.allowed and any("review" in b for b in dec.blockers)


def test_export_blocked_when_not_ready():
    d = build_dossier("p", "c", reproducibility=0.4, limitations=["computational only"])
    dec = evaluate_export(d, _approved_review(d) if False else None)
    assert not dec.allowed


def test_export_blocked_with_unresolved_contradiction():
    d = _ready_dossier(unresolved_contradictions=1)
    r = _approved_review(d)
    with pytest.raises(ExportBlocked):
        export_dossier(d, r, "/tmp/never_written_acero")


def test_approved_export_writes_locally_and_never_publishes(tmp_path):
    d = _ready_dossier()
    r = _approved_review(d)
    res = export_dossier(d, r, str(tmp_path / "out"))
    assert res["auto_published"] is False
    written = (tmp_path / "out" / "review_dossier.md").read_text()
    assert AI_USE_DECLARATION[:30] in written
    assert (tmp_path / "out" / "manifest.json").exists()
    assert (tmp_path / "out" / "checksums.txt").exists()


def test_export_payload_marks_local_only(tmp_path):
    import json
    d = _ready_dossier()
    r = _approved_review(d)
    export_dossier(d, r, str(tmp_path / "out"))
    payload = json.loads((tmp_path / "out" / "review_dossier.json").read_text())
    assert payload["destination"] == "local_only"
    assert payload["auto_published"] is False


# --- Codex-audit regression fixes (Sprint 12) -----------------------------

def test_approval_requires_a_stated_reason():
    """Anti rubber-stamp: an APPROVE with no reason is refused."""
    d = _ready_dossier()
    r = HumanReviewSession(dossier_id=d.id, reviewer="Merari", comprehension_ok=True)
    for s in ("central_claim", "main_evidence", "main_counter_evidence", "limitations",
              "reliability", "what_remains_to_validate_externally"):
        r.acknowledge(s)
    with pytest.raises(ReviewError):
        r.record(ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW, dossier=d, reasons=["  "])


def test_export_blocked_if_dossier_changed_after_approval():
    """The approval binds to the exact reviewed content; a later edit blocks export."""
    d = _ready_dossier()
    r = _approved_review(d)
    assert evaluate_export(d, r).allowed
    d.central_claim = "a SECRETLY stronger claim added after review"   # tamper
    dec = evaluate_export(d, r)
    assert not dec.allowed
    assert any("bind" in b for b in dec.blockers)
    with pytest.raises(ExportBlocked):
        export_dossier(d, r, "/tmp/never_written_acero_2")
