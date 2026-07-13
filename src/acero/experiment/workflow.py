"""Research workflow state machine (Sprint 4).

Enforces the ordered path from a defined question to a closed, human-reviewed
investigation. Illegal jumps (e.g. RUNNING before EXPERIMENT_APPROVED) are rejected.
"""

from __future__ import annotations

from enum import Enum

from ..core.errors import WorkflowError


class WorkflowState(str, Enum):
    QUESTION_DEFINED = "QUESTION_DEFINED"
    BACKGROUND_REVIEWED = "BACKGROUND_REVIEWED"
    ASSUMPTIONS_RECORDED = "ASSUMPTIONS_RECORDED"
    HYPOTHESES_PROPOSED = "HYPOTHESES_PROPOSED"
    PREDICTIONS_PREREGISTERED = "PREDICTIONS_PREREGISTERED"
    EXPERIMENT_DESIGNED = "EXPERIMENT_DESIGNED"
    EXPERIMENT_APPROVED = "EXPERIMENT_APPROVED"
    RUNNING = "RUNNING"
    RESULTS_CAPTURED = "RESULTS_CAPTURED"
    FALSIFICATION_REVIEW = "FALSIFICATION_REVIEW"
    REPRODUCIBILITY_CHECK = "REPRODUCIBILITY_CHECK"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    CLOSED = "CLOSED"


_ORDER = list(WorkflowState)
_INDEX = {s: i for i, s in enumerate(_ORDER)}


def next_states(state: WorkflowState) -> set[WorkflowState]:
    """Only forward-by-one is allowed (no skipping); any state may abort to CLOSED."""
    i = _INDEX[state]
    allowed: set[WorkflowState] = set()
    if i + 1 < len(_ORDER):
        allowed.add(_ORDER[i + 1])
    allowed.add(WorkflowState.CLOSED)
    return allowed


class ResearchWorkflow:
    """Tracks and validates the workflow state for one investigation."""

    def __init__(self, state: WorkflowState = WorkflowState.QUESTION_DEFINED) -> None:
        self.state = state
        self.history: list[WorkflowState] = [state]

    def advance(self, to: WorkflowState) -> WorkflowState:
        if to not in next_states(self.state):
            raise WorkflowError(
                f"Illegal workflow transition {self.state.value} -> {to.value}. "
                f"Allowed: {sorted(s.value for s in next_states(self.state))}"
            )
        self.state = to
        self.history.append(to)
        return self.state

    def require(self, state: WorkflowState) -> None:
        """Assert the workflow has reached at least ``state``."""
        if _INDEX[self.state] < _INDEX[state]:
            raise WorkflowError(
                f"Operation requires state >= {state.value}, but current is {self.state.value}."
            )
