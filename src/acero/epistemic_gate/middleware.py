"""Gate observability: metrics and structured traces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import GateResult

if TYPE_CHECKING:
    from .enforcement import GateProtectedAction


@dataclass
class GateMetrics:
    evaluated: int = 0
    allowed: int = 0
    blocked: int = 0
    warnings: int = 0
    overrides: int = 0
    rollbacks: int = 0
    bypass_attempts: int = 0
    rule_triggers: Counter[str] = field(default_factory=Counter)
    stage_blocks: Counter[str] = field(default_factory=Counter)

    def record_evaluated(self, stage: str, result: GateResult) -> None:
        self.evaluated += 1
        for r in result.results:
            if not r.passed and r.evaluable:
                self.rule_triggers[r.rule_id] += 1

    def record_allowed(self, stage: str) -> None:
        self.allowed += 1

    def record_blocked(self, stage: str, blockers: list[str]) -> None:
        self.blocked += 1
        self.stage_blocks[stage] += 1

    def record_warning(self, stage: str) -> None:
        self.warnings += 1

    def record_override(self, stage: str) -> None:
        self.overrides += 1

    def record_rollback(self) -> None:
        self.rollbacks += 1

    def record_bypass(self) -> None:
        self.bypass_attempts += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluated": self.evaluated, "allowed": self.allowed,
            "blocked": self.blocked, "warnings": self.warnings,
            "overrides": self.overrides, "rollbacks": self.rollbacks,
            "bypass_attempts": self.bypass_attempts,
            "top_rules": self.rule_triggers.most_common(8),
            "stage_blocks": dict(self.stage_blocks),
        }


@dataclass
class GateTrace:
    """In-memory ring of the most recent protected actions, for `gate trace`."""

    max_len: int = 500
    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, gpa: GateProtectedAction) -> None:
        self.entries.append(gpa.as_dict())
        if len(self.entries) > self.max_len:
            self.entries.pop(0)

    def get(self, action_id: str) -> dict[str, Any] | None:
        for e in reversed(self.entries):
            if e.get("action_id") == action_id:
                return e
        return None

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return self.entries[-n:]
