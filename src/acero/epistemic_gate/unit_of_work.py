"""Local multi-store Unit of Work (Sprint 11).

Coordinates a scientific action that touches several stores (ledger, provenance, World
Model, learner model, gate report, experiment registry) so it is all-or-nothing WITHOUT
distributed infrastructure. The gate runs BEFORE any mutation; each step registers a
compensating rollback. If any step fails: roll back, preserve the attempt and logs, and
leave no partial confidence, no granted understanding, and no lost negative result.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.clock import now_iso


class UoWState(str, Enum):
    PREPARED = "PREPARED"
    GATE_PASSED = "GATE_PASSED"
    MUTATING = "MUTATING"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


@dataclass
class Step:
    name: str
    do: Callable[[], Any]
    undo: Callable[[], None] | None = None


@dataclass
class UnitOfWork:
    action: str
    state: UoWState = UoWState.PREPARED
    steps: list[Step] = field(default_factory=list)
    done: list[Step] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    attempt_log: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=now_iso)

    def add(self, name: str, do: Callable[[], Any],
            undo: Callable[[], None] | None = None) -> None:
        self.steps.append(Step(name, do, undo))

    def gate_passed(self) -> None:
        self.state = UoWState.GATE_PASSED

    def commit(self) -> dict[str, Any]:
        """Run every step; on any failure, roll back the ones already done."""
        if self.state not in (UoWState.GATE_PASSED, UoWState.PREPARED):
            raise RuntimeError(f"cannot commit from {self.state}")
        self.state = UoWState.MUTATING
        for step in self.steps:
            self.attempt_log.append(f"do:{step.name}")
            try:
                self.results[step.name] = step.do()
                self.done.append(step)
            except Exception as exc:  # noqa: BLE001 - convert to rollback
                self.error = f"{type(exc).__name__}: {exc}"
                self.attempt_log.append(f"fail:{step.name}:{self.error}")
                self.rollback()
                self.state = UoWState.FAILED
                raise
        self.state = UoWState.COMMITTED
        return self.results

    def rollback(self) -> None:
        for step in reversed(self.done):
            if step.undo is None:
                continue
            self.attempt_log.append(f"undo:{step.name}")
            try:
                step.undo()
            except Exception:  # noqa: BLE001 - best-effort compensation
                self.attempt_log.append(f"undo_failed:{step.name}")
        self.done.clear()
        if self.state != UoWState.FAILED:
            self.state = UoWState.ROLLED_BACK

    def as_dict(self) -> dict[str, Any]:
        return {"action": self.action, "state": self.state.value,
                "n_steps": len(self.steps), "n_done": len(self.done),
                "error": self.error, "attempt_log": self.attempt_log}
