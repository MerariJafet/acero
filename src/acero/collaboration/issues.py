"""Review issue tracker (Sprint 19). Turns imported reviews into tracked, ownable issues."""

from __future__ import annotations

from ..discovery.store import DiscoveryStore
from .models import ExternalReview, IssueStatus, ReviewIssue

ISSUE_SCOPE = "_review_issues"


class IssueTracker:
    def __init__(self, store: DiscoveryStore) -> None:
        self._store = store

    def from_review(self, review: ExternalReview) -> list[ReviewIssue]:
        """Create OPEN issues from a review's concerns (critical for major, etc.)."""
        issues: list[ReviewIssue] = []
        for concern in review.major_concerns:
            issues.append(ReviewIssue(review_id=review.review_id, severity="high",
                                      description=concern))
        for concern in review.minor_concerns:
            issues.append(ReviewIssue(review_id=review.review_id, severity="low",
                                      description=concern))
        for c in review.claim_comments:
            issues.append(ReviewIssue(review_id=review.review_id, severity="medium",
                                      claim=str(c.get("claim", "")),
                                      description=str(c.get("comment", ""))))
        for i in issues:
            self._store.put(ISSUE_SCOPE, "issue", i.issue_id, i.model_dump(),
                            status=i.status.value, summary=f"issue[{i.severity}]")
        return issues

    def set_status(self, issue_id: str, status: IssueStatus, *, validation: str = ""
                   ) -> ReviewIssue:
        raw = self._store.get(issue_id)
        if raw is None:
            raise KeyError(issue_id)
        i = ReviewIssue(**raw)
        i.status = status
        i.validation = validation or i.validation
        self._store.put(ISSUE_SCOPE, "issue", i.issue_id, i.model_dump(),
                        status=status.value, summary=f"issue -> {status.value}")
        return i

    def all(self, *, review_id: str | None = None) -> list[ReviewIssue]:
        out = [ReviewIssue(**r)
               for r in self._store.list_objects(ISSUE_SCOPE, kind="issue")]
        return [i for i in out if review_id is None or i.review_id == review_id]

    def unresolved_critical(self) -> list[ReviewIssue]:
        return [i for i in self.all()
                if i.severity in ("critical", "high")
                and i.status in (IssueStatus.OPEN, IssueStatus.ACKNOWLEDGED,
                                 IssueStatus.IN_PROGRESS)]
