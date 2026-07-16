"""External Review Preparation Gauntlet (Sprint 19).

Ten cases that the collaboration/external-review machinery must handle correctly: a bundle
prepared, a correct- vs wrong-version review, a tampered bundle, an invalid reviewer schema, a
comment without a claim, an ignored critical issue, an unapproved response, an incompatible
license, AI authorship, and an absent external validation. None of these should be mishandled,
and none should be treated as real external validation.
"""

from __future__ import annotations

from typing import Any

from ..collaboration.bundle import BundleError, build_bundle
from ..collaboration.issues import IssueTracker
from ..collaboration.licensing import check_licenses
from ..collaboration.models import (
    ContributionMatrix,
    ExternalReview,
    ReviewerRole,
)
from ..collaboration.responses import ResponseKind, draft_response
from ..collaboration.review_import import (
    ReviewImportError,
    comment_has_claim,
    import_review,
)

_VERSION = "2.0.0-rc2"


def _bundle(tmp: str, *, licenses: dict[str, str] | None = None) -> dict[str, Any]:
    return build_bundle(
        tmp, project="Stellar variability", central_claims=[{"claim": "~11yr cycle"}],
        methods="FFT + AR(1) surrogate + bootstrap", evidence_map=[{"id": "e1"}],
        counterevidence=[{"id": "c1"}], limitations=["single dataset"],
        reliability_card={"adversarial_robustness": 1.0}, commit=_VERSION,
        licenses=licenses or {"code": "MIT", "data": "public-domain"})


def _review(version: str, **kw: Any) -> dict[str, Any]:
    base = {"reviewer_role": "STATISTICIAN", "reviewed_version": version,
            "overall_assessment": "solid", "major_concerns": [], "confidence": 0.6}
    base.update(kw)
    return base


def case1_bundle_prepared(tmp: str) -> dict[str, Any]:
    b = _bundle(tmp)
    return {"n_files": b["n_files"], "not_published": not b["auto_published"],
            "passed": b["n_files"] >= 12 and not b["auto_published"]}


def case2_correct_version_review() -> dict[str, Any]:
    try:
        r = import_review(_review(_VERSION), current_version=_VERSION)
        return {"imported": True, "trusted": r.trusted, "passed": not r.trusted}
    except ReviewImportError:
        return {"imported": False, "passed": False}


def case3_wrong_version_review() -> dict[str, Any]:
    try:
        import_review(_review("1.0.0-old"), current_version=_VERSION)
        return {"blocked": False, "passed": False}
    except ReviewImportError:
        return {"blocked": True, "passed": True}


def case4_tampered_bundle() -> dict[str, Any]:
    try:
        import_review(_review(_VERSION, reviewed_bundle_hash="OLDHASH"),
                      current_version=_VERSION, current_bundle_hash="NEWHASH")
        return {"blocked": False, "passed": False}
    except ReviewImportError:
        return {"blocked": True, "passed": True}


def case5_invalid_reviewer_schema() -> dict[str, Any]:
    try:
        import_review(_review(_VERSION, reviewer_role="SUPREME_LEADER"),
                      current_version=_VERSION)
        return {"blocked": False, "passed": False}
    except ReviewImportError:
        return {"blocked": True, "passed": True}


def case6_comment_without_claim() -> dict[str, Any]:
    ok = comment_has_claim({"claim": "the period", "comment": "check aliasing"})
    bad = comment_has_claim({"comment": "vague"})
    return {"anchored_ok": ok, "unanchored_rejected": not bad,
            "passed": ok and not bad}


def case7_critical_issue_not_ignored(disc_store) -> dict[str, Any]:
    tracker = IssueTracker(disc_store)
    review = ExternalReview(reviewer_role=ReviewerRole.METHODS_REVIEWER,
                            reviewed_version=_VERSION,
                            major_concerns=["the null model is wrong"])
    created = tracker.from_review(review)
    # scope to THIS review's issues (the store may persist issues from other runs)
    unresolved_ids = {i.issue_id for i in tracker.unresolved_critical()}
    mine_unresolved = [i for i in created if i.issue_id in unresolved_ids]
    return {"n_unresolved_critical": len(mine_unresolved),
            "passed": len(mine_unresolved) == 1}


def case8_incompatible_license(tmp: str) -> dict[str, Any]:
    try:
        _bundle(tmp, licenses={"data": "proprietary"})
        return {"blocked": False, "passed": False}
    except BundleError:
        return {"blocked": True, "passed": True}


def case9_ai_authorship() -> dict[str, Any]:
    cm = ContributionMatrix(human_author="Merari",
                            roles={"software": True, "methodology": True},
                            ai_assistance=["computation", "drafting"])
    return {"ai_listed_as_author": cm.ai_listed_as_author(),
            "passed": cm.ai_listed_as_author() is False}


def case10_unapproved_response() -> dict[str, Any]:
    draft = draft_response("iss1", ResponseKind.PARTIALLY_ACCEPTED, "will add a control")
    ai_blocked = False
    try:
        draft.approve("ACERO")
    except ValueError:
        ai_blocked = True
    return {"draft_unapproved": not draft.human_approved, "ai_approval_blocked": ai_blocked,
            "passed": not draft.human_approved and ai_blocked}


def case10b_license_unknown_blocked() -> dict[str, Any]:
    r = check_licenses({"figures": "unspecified"})
    return {"blocked": not r["ok"], "passed": not r["ok"]}


def run_external_review_gauntlet(tmp_dir: str, disc_store) -> dict[str, Any]:
    import os
    cases = {
        "1_bundle_prepared": case1_bundle_prepared(os.path.join(tmp_dir, "b1")),
        "2_correct_version": case2_correct_version_review(),
        "3_wrong_version": case3_wrong_version_review(),
        "4_tampered_bundle": case4_tampered_bundle(),
        "5_invalid_reviewer": case5_invalid_reviewer_schema(),
        "6_comment_without_claim": case6_comment_without_claim(),
        "7_critical_issue_tracked": case7_critical_issue_not_ignored(disc_store),
        "8_incompatible_license": case8_incompatible_license(os.path.join(tmp_dir, "b8")),
        "9_ai_authorship_blocked": case9_ai_authorship(),
        "10_unapproved_response": case10_unapproved_response(),
        "10b_unknown_license": case10b_license_unknown_blocked(),
    }
    return {"cases": cases, "n": len(cases),
            "passed": sum(1 for c in cases.values() if c["passed"]),
            "all_passed": all(c["passed"] for c in cases.values())}
