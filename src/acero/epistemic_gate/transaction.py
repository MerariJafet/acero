"""Thread-local gate context + transactional safety for protected mutations.

A protected mutation must run INSIDE a gate context that was opened only after the gate
PASSED. `gate_context()` opens that window; `require_context()` (called by guarded
persistence) raises BypassDetected if no window is open — so a direct write that skips the
gate is caught at runtime, not just by developer discipline.

Enforcement is opt-in via ENFORCE_INLINE_GATE so legacy code paths keep working; guarded
wrappers enable it around their own writes.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

# Global switch. Guarded wrappers turn this on; when off, require_context is a no-op so
# existing (pre-Sprint-10) call sites are unaffected.
ENFORCE_INLINE_GATE = False

_state = threading.local()


@dataclass
class _Ctx:
    action: str
    stage: str
    tokens: list[str] = field(default_factory=list)


def _stack() -> list[_Ctx]:
    if not hasattr(_state, "stack"):
        _state.stack = []
    return _state.stack


@contextmanager
def gate_context(action: str, stage: str, token: str) -> Iterator[_Ctx]:
    """Open a window in which protected mutations for ``action`` are permitted."""
    ctx = _Ctx(action=action, stage=stage)
    ctx.tokens.append(token)
    _stack().append(ctx)
    try:
        yield ctx
    finally:
        _stack().pop()


def in_context() -> bool:
    return bool(_stack())


def current() -> _Ctx | None:
    st = _stack()
    return st[-1] if st else None


def require_context(where: str) -> None:
    """Raise BypassDetected if enforcement is on and no gate context is open."""
    if not ENFORCE_INLINE_GATE:
        return
    if not in_context():
        from .exceptions import BypassDetected

        raise BypassDetected(where)


@contextmanager
def enforcement_enabled() -> Iterator[None]:
    """Temporarily turn on inline enforcement (used by guarded wrappers/tests)."""
    global ENFORCE_INLINE_GATE
    prev = ENFORCE_INLINE_GATE
    ENFORCE_INLINE_GATE = True
    try:
        yield
    finally:
        ENFORCE_INLINE_GATE = prev


@dataclass
class Transaction:
    """A minimal transactional guard: collects a rollback callback so a blocked or failed
    mutation leaves no partial state. SQLAlchemy sessions are the real atomicity unit; this
    records intent and runs compensating actions when a mutation raises after starting."""

    _rollbacks: list[Any] = field(default_factory=list)
    committed: bool = False

    def on_rollback(self, fn: Any) -> None:
        self._rollbacks.append(fn)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        for fn in reversed(self._rollbacks):
            try:
                fn()
            except Exception:  # noqa: BLE001 - best-effort compensation
                pass
        self._rollbacks.clear()
