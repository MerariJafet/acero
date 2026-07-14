"""Decorator sugar for gate-protected service methods.

`@gate_protected(stage, action, artifact_fn)` wraps a method so it runs through a shared
GateEnforcer before its body executes. The wrapped object must expose a GateEnforcer as
`self._enforcer`; ``artifact_fn`` builds the gate artifact from the call arguments.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from .models import Stage


def gate_protected(stage: Stage, action: str,
                   artifact_fn: Callable[..., dict[str, Any]]) -> Callable[..., Any]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            enforcer = getattr(self, "_enforcer", None)
            if enforcer is None:
                # No enforcer wired → behave as before (legacy path).
                return fn(self, *args, **kwargs)
            artifact = artifact_fn(self, *args, **kwargs)
            override = kwargs.pop("override", None)
            _gpa, result = enforcer.enforce(
                action=action, stage=stage, artifact=artifact,
                mutation=lambda: fn(self, *args, **kwargs),
                context={"actor": kwargs.get("actor", "system")},
                override=override)
            return result
        return wrapper
    return decorator
