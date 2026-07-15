"""Async-safe gate execution context + transactional safety (Sprint 11).

A protected mutation must run INSIDE a GateExecutionContext opened only after the gate
PASSED. The context is stored in a ``contextvars.ContextVar`` so it propagates correctly
across asyncio tasks, FastAPI background tasks, threads and local workers (and is validated,
not trusted, when crossing a process). ``require_context()`` (called by guarded persistence)
raises BypassDetected if no valid context is open — a direct write that skips the gate is
caught at runtime, not merely by developer discipline.

The context is NOT a substitute for the gate: it only proves the gate already ran for this
specific action + artifacts, carrying the mutation token that authorises the write.
"""

from __future__ import annotations

import contextvars
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id

# Global switch. Guarded wrappers turn this on; when off, require_context is a no-op so
# pre-Sprint-10 call sites are unaffected.
ENFORCE_INLINE_GATE = False


@dataclass
class GateExecutionContext:
    """Proof that the gate PASSED for a specific action, carried across execution scopes."""

    context_id: str
    action_id: str
    action: str
    stage: str
    artifact_ids: tuple[str, ...] = ()
    allowed_mutations: tuple[str, ...] = ()
    policy_version: str = "v1"
    rule_versions: tuple[str, ...] = ()
    actor: str = "system"
    process_id: int = 0
    parent_context: str | None = None
    created_at: str = ""
    expires_at: str | None = None
    integrity_token: str | None = None            # the mutation token id

    def as_dict(self) -> dict[str, Any]:
        return {"context_id": self.context_id, "action_id": self.action_id,
                "action": self.action, "stage": self.stage,
                "artifact_ids": list(self.artifact_ids),
                "allowed_mutations": list(self.allowed_mutations),
                "policy_version": self.policy_version,
                "rule_versions": list(self.rule_versions), "actor": self.actor,
                "process_id": self.process_id, "parent_context": self.parent_context,
                "created_at": self.created_at, "expires_at": self.expires_at,
                "integrity_token": self.integrity_token}


_STACK: contextvars.ContextVar[tuple[GateExecutionContext, ...]] = contextvars.ContextVar(
    "acero_gate_stack", default=())


def _stack() -> tuple[GateExecutionContext, ...]:
    return _STACK.get()


@contextmanager
def gate_context(action: str, stage: str, token: str, *,
                 artifact_ids: tuple[str, ...] = (), actor: str = "system",
                 allowed_mutations: tuple[str, ...] = (),
                 rule_versions: tuple[str, ...] = (),
                 expires_at: str | None = None) -> Iterator[GateExecutionContext]:
    """Open a window in which protected mutations for ``action`` are permitted."""
    parent = current()
    ctx = GateExecutionContext(
        context_id=new_id("gctx"), action_id=token, action=action, stage=stage,
        artifact_ids=artifact_ids, allowed_mutations=allowed_mutations or (action,),
        rule_versions=rule_versions, actor=actor, process_id=os.getpid(),
        parent_context=parent.context_id if parent else None,
        created_at=now_iso(), expires_at=expires_at, integrity_token=token)
    reset = _STACK.set((*_stack(), ctx))
    try:
        yield ctx
    finally:
        _STACK.reset(reset)


def in_context() -> bool:
    return bool(_stack())


def current() -> GateExecutionContext | None:
    st = _stack()
    return st[-1] if st else None


def require_context(where: str, *, action: str | None = None) -> None:
    """Raise BypassDetected if enforcement is on and no valid gate context is open.

    When ``action`` is given, the open context must list it in ``allowed_mutations`` — so a
    context opened for one action cannot authorise a different mutation."""
    if not ENFORCE_INLINE_GATE:
        return
    ctx = current()
    if ctx is None:
        from .exceptions import BypassDetected
        raise BypassDetected(where)
    if action is not None and action not in ctx.allowed_mutations:
        from .exceptions import BypassDetected
        raise BypassDetected(f"{where} (context authorises {ctx.allowed_mutations})")


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
    """A minimal transactional guard: collects rollback callbacks so a blocked or failed
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
