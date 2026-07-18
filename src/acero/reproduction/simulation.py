"""External review SIMULATION (Sprint 25 §25.6).

Fixtures modelling the kinds of reviews a bundle might receive. The system
RECORDS each simulated review and its verification status — it NEVER auto-accepts
a review as truth, never treats a favorable review as validation, and never treats
model/AI agreement as evidence. Real external review requires real, independent
humans and is out of scope here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulatedReview:
    kind: str
    verdict: str                     # reviewer's stated verdict
    verified: bool                   # did tamper/version checks pass?
    trusted: bool                    # ACERO's trust — ALWAYS False (records only)
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "verdict": self.verdict, "verified": self.verified,
                "trusted": self.trusted, "notes": self.notes}


@dataclass
class ReviewLedger:
    """Records reviews; auto-acceptance is impossible by construction."""
    reviews: list[SimulatedReview] = field(default_factory=list)

    def record(self, review: SimulatedReview) -> None:
        review.trusted = False       # invariant: never auto-trust a review
        self.reviews.append(review)

    def summary(self) -> dict[str, Any]:
        return {"n": len(self.reviews),
                "any_auto_trusted": any(r.trusted for r in self.reviews),
                "verified": sum(1 for r in self.reviews if r.verified),
                "reviews": [r.as_dict() for r in self.reviews]}


# The ten fixture kinds required by the sprint. Each pairs a reviewer verdict with
# whether the bundle's integrity checks would pass for that scenario.
FIXTURES: list[tuple[str, str, bool, str]] = [
    ("correct_review", "reproduces", True, "careful, verified reproduction"),
    ("superficial_favorable", "looks good", True, "favorable but shallow — not validation"),
    ("valid_critique", "needs changes", True, "identifies a real red-noise weakness"),
    ("wrong_critique", "does not reproduce", True, "reviewer error; bundle verifies fine"),
    ("tampered", "reproduces", False, "files modified after signing"),
    ("wrong_version", "reproduces", False, "review is against a different version"),
    ("unsigned", "reproduces", False, "no signature where one was required"),
    ("conflict_of_interest", "reproduces", True, "undeclared conflict flagged"),
    ("failed_reproduction", "does not reproduce", True, "honest failure to reproduce"),
    ("missing_evidence", "cannot assess", False, "referenced evidence file absent"),
]


def run_simulation() -> dict[str, Any]:
    ledger = ReviewLedger()
    for kind, verdict, verified, notes in FIXTURES:
        ledger.record(SimulatedReview(kind=kind, verdict=verdict, verified=verified,
                                      trusted=False, notes=notes))
    s = ledger.summary()
    s["invariant_no_auto_trust"] = not s["any_auto_trusted"]
    s["note"] = ("Favorable reviews are recorded, not accepted. Verification status is "
                 "independent of the reviewer's verdict. AI/model agreement is not evidence.")
    return s
