"""Exceptions for the inline epistemic gate."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import GateResult


class GateError(Exception):
    """Base class for gate-enforcement errors."""


class GateBlockedError(GateError):
    """A protected mutation was blocked by the gate; NO mutation was performed."""

    def __init__(self, action: str, result: GateResult) -> None:
        self.action = action
        self.result = result
        blockers = ", ".join(b.rule_id for b in result.blockers) or "—"
        super().__init__(f"gate BLOCKED '{action}' [{result.stage}]: {blockers}")


class OverrideNotAllowed(GateError):
    """A human tried to override a non-overridable rule (e.g. fabricated result)."""

    def __init__(self, action: str, rules: list[str]) -> None:
        self.action = action
        self.rules = rules
        super().__init__(
            f"override refused for '{action}': non-overridable rule(s) {rules}")


class BypassDetected(GateError):
    """A protected mutation was attempted OUTSIDE an active gate context."""

    def __init__(self, where: str) -> None:
        super().__init__(
            f"protected mutation '{where}' attempted without passing the gate")
