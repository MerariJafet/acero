"""Helpers for declaring gate rules concisely.

``must_be_true`` / ``must_be_false`` build a checker over a boolean flag in the artifact:
a MISSING flag raises NotEvaluable (recorded as a can't-evaluate warning) rather than
silently passing — the gate never pretends to have checked something it couldn't.
"""

from __future__ import annotations

from typing import Any

from ..models import Checker, GateRule, NotEvaluable, Severity, Stage


def must_be_true(key: str, detail: str) -> Checker:
    def check(a: dict[str, Any]) -> str | None:
        if key not in a:
            raise NotEvaluable(f"missing input '{key}'")
        return None if a[key] else detail
    return check


def must_be_false(key: str, detail: str) -> Checker:
    def check(a: dict[str, Any]) -> str | None:
        if key not in a:
            raise NotEvaluable(f"missing input '{key}'")
        return detail if a[key] else None
    return check


def rule(rule_id: str, stage: Stage, key: str, *, expect: bool, detail: str,
         remediation: str, severity: Severity = Severity.BLOCKER,
         source: str = "constitution", version: str = "v1") -> GateRule:
    checker = must_be_true(key, detail) if expect else must_be_false(key, detail)
    return GateRule(id=rule_id, stage=stage, severity=severity, description=detail,
                    checker=checker, inputs=(key,), failure_message=detail,
                    remediation=remediation, source=source, version=version)
