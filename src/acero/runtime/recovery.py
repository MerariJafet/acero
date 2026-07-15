"""Restart & failure recovery decisions (Sprint 14).

Given a task's persisted state after a crash/restart/timeout, decide what to do:
RESUME (checkpoint present, attempts remain), RETRY (no checkpoint, attempts remain),
ROLLBACK (partial mutation with no checkpoint), DEAD_LETTER (attempts exhausted), or
HUMAN_REVIEW (inconsistent: result written but not recorded, or record without artifact).
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class RecoveryDecision(str, Enum):
    RESUME = "RESUME"
    RETRY = "RETRY"
    ROLLBACK = "ROLLBACK"
    DEAD_LETTER = "DEAD_LETTER"
    HUMAN_REVIEW = "HUMAN_REVIEW"


def decide(task: dict[str, Any], *, artifact_present: bool = True,
           record_present: bool = True) -> RecoveryDecision:
    """Decide recovery for a task recovered after a fault."""
    attempts = task.get("attempts", 0)
    max_attempts = task.get("max_attempts", 3)
    checkpoint = task.get("checkpoint") or {}

    # inconsistency between the durable record and the artifact (result written but not
    # recorded, or record without artifact) → a human must reconcile.
    if record_present != artifact_present:
        return RecoveryDecision.HUMAN_REVIEW
    if attempts >= max_attempts:
        return RecoveryDecision.DEAD_LETTER
    # a partial mutation with no checkpoint must be rolled back before any retry
    if task.get("partial_mutation") and not checkpoint:
        return RecoveryDecision.ROLLBACK
    if checkpoint:
        return RecoveryDecision.RESUME
    return RecoveryDecision.RETRY
