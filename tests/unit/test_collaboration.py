"""Sprint 19 tests: collaboration workspace, bundle, import, issues, responses, authorship."""

from __future__ import annotations

import pytest

from acero.collaboration.bundle import BlindMode, BundleError, build_bundle
from acero.collaboration.engine import DRAFT_KINDS, CollaborationEngine
from acero.collaboration.issues import IssueTracker
from acero.collaboration.licensing import check_licenses
from acero.collaboration.models import (
    CREDIT_ROLES,
    ContributionMatrix,
    ExternalReview,
    IssueStatus,
    ReviewerRole,
)
from acero.collaboration.questions import questions_for
from acero.collaboration.responses import ResponseKind, draft_response
from acero.collaboration.review_import import (
    ReviewImportError,
    comment_has_claim,
    import_review,
)

_V = "2.0.0-rc2"


def _review_payload(version=_V, **kw):
    p = {"reviewer_role": "STATISTICIAN", "reviewed_version": version,
         "overall_assessment": "ok", "confidence": 0.6}
    p.update(kw)
    return p


# --- bundle ---------------------------------------------------------------

def _build(tmp, licenses=None, blind=BlindMode.OPEN_IDENTITY):
    return build_bundle(
        tmp, project="p", central_claims=[{"claim": "c"}], methods="m",
        evidence_map=[{"id": "e"}], counterevidence=[{"id": "ce"}], limitations=["lim"],
        reliability_card={"x": 1.0}, commit=_V,
        licenses=licenses or {"code": "MIT"}, blind=blind)


def test_bundle_written_locally_never_published(tmp_path):
    r = _build(str(tmp_path / "b"))
    assert r["auto_published"] is False and r["n_files"] >= 12
    assert (tmp_path / "b" / "AI_USE.md").exists()
    assert (tmp_path / "b" / "checksums.txt").exists()
    assert (tmp_path / "b" / "version_binding.json").exists()


def test_bundle_blocked_on_incompatible_license(tmp_path):
    with pytest.raises(BundleError):
        _build(str(tmp_path / "b"), licenses={"data": "proprietary"})


def test_blinded_bundle_hides_identity_but_keeps_reproduction(tmp_path):
    _build(str(tmp_path / "b"), blind=BlindMode.BLINDED)
    summary = (tmp_path / "b" / "executive_summary.md").read_text()
    assert "[blinded]" in summary
    assert (tmp_path / "b" / "evidence_map.json").exists()   # reproduction info retained


# --- structured import + version binding ----------------------------------

def test_import_is_never_auto_trusted():
    r = import_review(_review_payload(), current_version=_V)
    assert r.trusted is False


def test_import_rejects_wrong_version():
    with pytest.raises(ReviewImportError):
        import_review(_review_payload(version="0.1"), current_version=_V)


def test_import_rejects_bundle_hash_mismatch():
    with pytest.raises(ReviewImportError):
        import_review(_review_payload(reviewed_bundle_hash="OLD"),
                      current_version=_V, current_bundle_hash="NEW")


def test_import_rejects_invalid_reviewer_role():
    with pytest.raises(ReviewImportError):
        import_review(_review_payload(reviewer_role="KING"), current_version=_V)


def test_comment_must_reference_a_claim():
    assert comment_has_claim({"claim": "x", "comment": "y"})
    assert not comment_has_claim({"comment": "unanchored"})


# --- issue tracker --------------------------------------------------------

def test_review_becomes_tracked_issues(disc_store):
    tracker = IssueTracker(disc_store)
    review = ExternalReview(reviewer_role=ReviewerRole.METHODS_REVIEWER,
                            reviewed_version=_V,
                            major_concerns=["null model wrong"], minor_concerns=["typo"])
    issues = tracker.from_review(review)
    assert len(issues) == 2
    assert len(tracker.unresolved_critical()) == 1        # the major concern


def test_critical_issue_stays_unresolved_until_status_change(disc_store):
    tracker = IssueTracker(disc_store)
    review = ExternalReview(reviewer_role=ReviewerRole.STATISTICIAN, reviewed_version=_V,
                            major_concerns=["leakage"])
    iid = tracker.from_review(review)[0].issue_id
    assert tracker.unresolved_critical()
    tracker.set_status(iid, IssueStatus.RESOLVED, validation="added held-out set")
    assert not tracker.unresolved_critical()


# --- responses (human approval) -------------------------------------------

def test_response_draft_requires_human_approval():
    d = draft_response("iss1", ResponseKind.PARTIALLY_ACCEPTED, "will add control")
    assert not d.human_approved
    with pytest.raises(ValueError):
        d.approve("ACERO")                            # AI cannot approve
    d.approve("Merari")
    assert d.human_approved and d.approver == "Merari"


# --- authorship + licensing -----------------------------------------------

def test_ai_never_listed_as_author():
    cm = ContributionMatrix(human_author="Merari", roles={"software": True},
                            ai_assistance=["computation"])
    assert cm.ai_listed_as_author() is False
    assert set(CREDIT_ROLES) >= {"software", "methodology", "validation"}


def test_unknown_license_blocks():
    assert not check_licenses({"figures": "unspecified"})["ok"]
    assert check_licenses({"code": "MIT", "data": "public-domain"})["ok"]


# --- workspace + drafts + validation plan ---------------------------------

def test_workspace_created_with_review_questions(disc_store):
    eng = CollaborationEngine(disc_store)
    ws = eng.create_workspace("proj", "get methods review",
                             expertise=[ReviewerRole.STATISTICIAN])
    assert ws.review_questions and ws.confidentiality == "local_only"
    assert eng.workspaces()


def test_draft_communication_is_never_sent(disc_store):
    eng = CollaborationEngine(disc_store)
    d = eng.draft_communication("review_request", purpose="methods review",
                               materials=["bundle"], reviewer_time_estimate="2h",
                               limitations=["single dataset"])
    assert d["sent"] is False and "ai_use" in d
    with pytest.raises(ValueError):
        eng.draft_communication("spam_everyone", purpose="", materials=[],
                               reviewer_time_estimate="", limitations=[])


def test_validation_plan_is_not_validation(disc_store):
    eng = CollaborationEngine(disc_store)
    plan = eng.validation_plan("the ~11yr cycle reflects the dynamo",
                              expertise=[ReviewerRole.DOMAIN_EXPERT])
    assert plan.blockers                              # nothing performed; blockers present


def test_questions_are_not_just_do_you_agree():
    qs = questions_for("STATISTICIAN")
    assert any("invalidate" in q.lower() for q in qs)
    assert any("independent" in q.lower() for q in qs)
    assert "review_request" in DRAFT_KINDS
