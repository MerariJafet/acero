"""Learning history and spaced-review scheduling.

The history is an append-only log of learning events, enough to reconstruct
"what did the researcher learn during this investigation?". Review scheduling is a
simple, honest heuristic — not a sophisticated SRS — driven by time since assessment,
concept importance, prior errors, recent use, transfer, overconfidence, and criticality
to active projects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from ...core.clock import now
from ..models import Criticality, KnowledgeState, KnowledgeStatus


@dataclass
class LearningEvent:
    kind: str                 # evidence|transition|misconception|prediction|override|review
    concept: str
    detail: str
    project_id: str | None = None
    timestamp: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningHistory:
    learner_id: str
    events: list[LearningEvent] = field(default_factory=list)

    def record(self, ev: LearningEvent) -> None:
        if not ev.timestamp:
            ev.timestamp = now().isoformat()
        self.events.append(ev)

    def for_project(self, project_id: str) -> list[LearningEvent]:
        return [e for e in self.events if e.project_id == project_id]

    def concepts_mastered(self) -> list[str]:
        return sorted({e.concept for e in self.events
                       if e.kind == "transition"
                       and e.payload.get("to") == KnowledgeStatus.MASTERED.value})

    def summary(self, project_id: str | None = None) -> dict[str, Any]:
        evs = self.for_project(project_id) if project_id else self.events
        by_kind: dict[str, int] = {}
        for e in evs:
            by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
        return {"learner_id": self.learner_id, "n_events": len(evs),
                "by_kind": by_kind,
                "concepts_touched": sorted({e.concept for e in evs}),
                "mastered": self.concepts_mastered()}


# Base intervals (days) by achieved status — higher mastery decays slower.
_BASE_DAYS: dict[KnowledgeStatus, int] = {
    KnowledgeStatus.RECOGNIZED: 2,
    KnowledgeStatus.PARTIALLY_UNDERSTOOD: 3,
    KnowledgeStatus.PROCEDURALLY_COMPETENT: 5,
    KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD: 9,
    KnowledgeStatus.TRANSFER_CAPABLE: 16,
    KnowledgeStatus.MASTERED: 30,
}
_CRIT_FACTOR = {Criticality.LOW: 1.5, Criticality.MEDIUM: 1.0,
                Criticality.HIGH: 0.6, Criticality.BLOCKING: 0.4}


def next_review(state: KnowledgeState, *, criticality: Criticality = Criticality.MEDIUM,
                n_prior_errors: int = 0, recently_used: bool = False,
                overconfident: bool = False) -> str:
    """Compute the next review timestamp. Shorter when the concept is critical, error-
    prone, unused, or where the learner is overconfident."""
    base = _BASE_DAYS.get(state.status, 1)
    factor = _CRIT_FACTOR.get(criticality, 1.0)
    factor *= 0.7 ** min(n_prior_errors, 4)          # more past errors → sooner
    if recently_used:
        factor *= 1.4                                # reinforced by use → later
    if overconfident:
        factor *= 0.6                                # dangerous → sooner
    days = max(1.0, base * factor)
    return (now() + timedelta(days=days)).isoformat()


def is_decayed(state: KnowledgeState, *, now_iso: str | None = None) -> bool:
    """A concept past its review date with no recent evidence is DECAYED."""
    if state.next_review is None:
        return False
    from datetime import datetime
    ref = datetime.fromisoformat(now_iso) if now_iso else now()
    try:
        due = datetime.fromisoformat(state.next_review)
    except ValueError:
        return False
    return ref > due
