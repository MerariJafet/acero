"""Structured human scientific review (Sprint 12).

Before an artifact can be marked ready for external human review, the researcher must
DEMONSTRATE understanding of the things that matter — the central claim, the main
supporting evidence, the main counter-evidence, the limitations, the reliability, and what
still needs external validation — and record an explicit decision. A review is never a
rubber stamp: unacknowledged critical sections block approval, and the reviewer must not be
ACERO. The decision, reasons, and a content hash are recorded (anti-tamper).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.clock import now_iso
from ..core.hashing import hash_json
from ..core.ids import new_id
from .dossier import ReviewDossier

# The sections the human MUST engage with before approving (ties to comprehension).
REQUIRED_ACKNOWLEDGEMENTS = (
    "central_claim", "main_evidence", "main_counter_evidence", "limitations",
    "reliability", "what_remains_to_validate_externally",
)


class ReviewDecision(str, Enum):
    APPROVE_FOR_EXTERNAL_REVIEW = "APPROVE_FOR_EXTERNAL_REVIEW"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    REJECT = "REJECT"
    # NOTE: there is no APPROVE_FOR_PUBLICATION — ACERO never publishes.


class ReviewError(RuntimeError):
    """Raised when a review is malformed (AI reviewer, missing acknowledgements, ...)."""


@dataclass
class HumanReviewSession:
    dossier_id: str
    reviewer: str                                     # must be a human, not ACERO
    acknowledged: dict[str, bool] = field(default_factory=dict)
    comprehension_ok: bool = False                    # from the Sprint-9 comprehension gate
    decision: ReviewDecision | None = None
    reasons: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("review"))
    timestamp: str = field(default_factory=now_iso)
    content_hash: str = ""

    def acknowledge(self, section: str) -> None:
        if section not in REQUIRED_ACKNOWLEDGEMENTS:
            raise ReviewError(f"unknown review section {section!r}")
        self.acknowledged[section] = True

    def missing_acknowledgements(self) -> list[str]:
        return [s for s in REQUIRED_ACKNOWLEDGEMENTS if not self.acknowledged.get(s)]

    def record(self, decision: ReviewDecision, *, dossier: ReviewDossier,
               reasons: list[str] | None = None) -> HumanReviewSession:
        """Record a decision. APPROVE requires a human reviewer, all acknowledgements, and
        demonstrated comprehension; otherwise it is refused."""
        if self.reviewer.strip().lower() in ("", "acero", "ai", "codex", "system"):
            raise ReviewError("the reviewer must be a human, not ACERO/AI")
        self.reasons = reasons or []
        if decision == ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW:
            missing = self.missing_acknowledgements()
            if missing:
                raise ReviewError(f"cannot approve: unacknowledged sections {missing}")
            if not self.comprehension_ok:
                raise ReviewError("cannot approve: comprehension not demonstrated")
            if not any(x.strip() for x in (reasons or [])):
                # a substantive approval requires the reviewer to state why (anti rubber-
                # stamp, Codex-audit fix)
                raise ReviewError("cannot approve without a stated reason")
        self.decision = decision
        self.timestamp = now_iso()
        self.content_hash = self._hash(dossier)
        return self

    def _hash(self, dossier: ReviewDossier) -> str:
        return hash_json({"dossier": dossier.as_dict(), "reviewer": self.reviewer,
                          "decision": self.decision.value if self.decision else None,
                          "acknowledged": self.acknowledged})

    def matches(self, dossier: ReviewDossier) -> bool:
        """True iff this recorded review binds to the EXACT current dossier content.

        Prevents exporting an approval for a dossier that was modified after review
        (Codex-audit fix)."""
        return bool(self.content_hash) and self.content_hash == self._hash(dossier)

    @property
    def approved(self) -> bool:
        return self.decision == ReviewDecision.APPROVE_FOR_EXTERNAL_REVIEW

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "dossier_id": self.dossier_id, "reviewer": self.reviewer,
                "acknowledged": self.acknowledged,
                "missing_acknowledgements": self.missing_acknowledgements(),
                "comprehension_ok": self.comprehension_ok,
                "decision": self.decision.value if self.decision else None,
                "reasons": self.reasons, "approved": self.approved,
                "timestamp": self.timestamp, "content_hash": self.content_hash}
