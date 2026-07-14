"""Data models for the Global Epistemic Gate."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.clock import now_iso


class Stage(str, Enum):
    LITERATURE = "LITERATURE"
    QUESTION = "QUESTION"
    HYPOTHESIS = "HYPOTHESIS"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    EXECUTION = "EXECUTION"
    INFERENCE = "INFERENCE"
    ANALOGY = "ANALOGY"
    DERIVATION = "DERIVATION"
    WORLD_MODEL_UPDATE = "WORLD_MODEL_UPDATE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PUBLICATION = "PUBLICATION"


class Severity(str, Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class GateOutcome(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    BLOCKED = "BLOCKED"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    BLOCKED_FOR_LEARNING = "BLOCKED_FOR_LEARNING"


# A checker inspects an artifact dict and returns a failure detail string if the rule is
# violated, None if it passes, or raises NotEvaluable if a required input is absent.
Checker = Callable[[dict[str, Any]], str | None]


class NotEvaluable(Exception):
    """Raised by a checker when a required input is missing (recorded as a warning)."""


@dataclass(frozen=True)
class GateRule:
    id: str
    stage: Stage
    severity: Severity
    description: str
    checker: Checker
    inputs: tuple[str, ...] = ()
    failure_message: str = ""
    remediation: str = ""
    deterministic: bool = True
    source: str = "constitution"
    version: str = "v1"


@dataclass
class RuleResult:
    rule_id: str
    stage: str
    severity: str
    passed: bool
    detail: str = ""
    remediation: str = ""
    evaluable: bool = True


@dataclass
class GateResult:
    stage: str
    outcome: GateOutcome
    results: list[RuleResult] = field(default_factory=list)
    responsible: str = "system"
    timestamp: str = field(default_factory=now_iso)
    version: str = "v1"

    @property
    def blockers(self) -> list[RuleResult]:
        return [r for r in self.results
                if not r.passed and r.severity == Severity.BLOCKER.value and r.evaluable]

    @property
    def warnings(self) -> list[RuleResult]:
        return [r for r in self.results
                if (not r.passed and r.severity == Severity.WARNING.value) or not r.evaluable]

    @property
    def passed_rules(self) -> list[RuleResult]:
        return [r for r in self.results if r.passed]

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage, "outcome": self.outcome.value,
            "n_rules": len(self.results), "n_passed": len(self.passed_rules),
            "n_blockers": len(self.blockers), "n_warnings": len(self.warnings),
            "blockers": [{"rule": r.rule_id, "detail": r.detail,
                          "remediation": r.remediation} for r in self.blockers],
            "warnings": [{"rule": r.rule_id, "detail": r.detail} for r in self.warnings],
            "responsible": self.responsible, "timestamp": self.timestamp,
            "version": self.version,
        }
