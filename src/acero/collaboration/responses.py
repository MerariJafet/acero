"""Review response drafts (Sprint 19). Codex may draft; a HUMAN must approve before use."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseKind(str, Enum):
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    REJECTED_WITH_RATIONALE = "rejected_with_rationale"
    REQUIRES_FURTHER_ANALYSIS = "requires_further_analysis"
    REQUIRES_NEW_EXPERIMENT = "requires_new_experiment"


@dataclass
class ResponseDraft:
    issue_id: str
    kind: ResponseKind
    text: str
    human_approved: bool = False
    approver: str | None = None
    _ai_drafted: bool = field(default=True)

    def approve(self, approver: str) -> None:
        if approver.strip().lower() in ("", "acero", "ai", "codex", "system"):
            raise ValueError("a response must be approved by a HUMAN, not ACERO/AI")
        self.human_approved = True
        self.approver = approver

    def as_dict(self) -> dict[str, Any]:
        return {"issue_id": self.issue_id, "kind": self.kind.value, "text": self.text,
                "ai_drafted": self._ai_drafted, "human_approved": self.human_approved,
                "approver": self.approver}


def draft_response(issue_id: str, kind: ResponseKind, rationale: str) -> ResponseDraft:
    """Produce a DRAFT (unapproved). Sending/using requires human approval."""
    return ResponseDraft(issue_id=issue_id, kind=kind,
                         text=f"[{kind.value}] {rationale}")
