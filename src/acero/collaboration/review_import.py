"""Structured review import + version binding (Sprint 19).

Imports an ExternalReview from a reviewer_form. It is NEVER auto-trusted: schema is validated,
and the review is checked to BIND to the current bundle version/fingerprint. A review written
against a different version does not apply to the new content.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .models import ExternalReview, ReviewerRole


class ReviewImportError(RuntimeError):
    """Raised when an imported review is malformed or does not bind to the version."""


def import_review(payload: dict[str, Any], *, current_version: str,
                  current_bundle_hash: str = "") -> ExternalReview:
    """Validate + version-bind an imported review. Trusted is always False."""
    # schema validation
    try:
        role = ReviewerRole(payload.get("reviewer_role", ""))
    except ValueError as exc:
        raise ReviewImportError(f"invalid reviewer_role: {payload.get('reviewer_role')}") from exc
    try:
        review = ExternalReview(
            reviewer_role=role,
            reviewed_version=str(payload.get("reviewed_version", "")),
            reviewed_bundle_hash=str(payload.get("reviewed_bundle_hash", "")),
            overall_assessment=str(payload.get("overall_assessment", "")),
            major_concerns=list(payload.get("major_concerns", [])),
            minor_concerns=list(payload.get("minor_concerns", [])),
            claim_comments=list(payload.get("claim_comments", [])),
            method_comments=list(payload.get("method_comments", [])),
            reproduction_result=str(payload.get("reproduction_result", "not_attempted")),
            requested_changes=list(payload.get("requested_changes", [])),
            confidence=float(payload.get("confidence", 0.5)),
            trusted=False)                          # NEVER auto-trusted
    except (ValidationError, ValueError, TypeError) as exc:
        raise ReviewImportError(f"schema validation failed: {exc}") from exc

    # version binding: the review must target the current version
    if review.reviewed_version != current_version:
        raise ReviewImportError(
            f"version mismatch: review targets {review.reviewed_version!r}, "
            f"current is {current_version!r} — review does not auto-apply")
    if current_bundle_hash and review.reviewed_bundle_hash and \
            review.reviewed_bundle_hash != current_bundle_hash:
        raise ReviewImportError("bundle hash mismatch: content changed since the review")
    return review


def comment_has_claim(comment: dict[str, Any]) -> bool:
    """A claim_comment must reference a claim (an unanchored comment is rejected)."""
    return bool(str(comment.get("claim", "")).strip())
