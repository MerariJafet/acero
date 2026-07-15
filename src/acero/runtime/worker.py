"""Local worker runtime (Sprint 14).

A worker claims a task (taking a lease), heartbeats while it runs the handler, persists
checkpoints, and completes/fails durably. Handlers run in-process here; long/untrusted
compute is delegated to the existing sandbox by the handler. Designed for `acero worker`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..core.ids import new_id
from .queue import ResearchQueue

# A handler receives (payload, checkpoint, heartbeat_fn) and returns a result dict. It may
# call heartbeat_fn(checkpoint) to renew the lease and persist progress.
Handler = Callable[[dict[str, Any], dict[str, Any], Callable[[dict[str, Any]], bool]], dict[str, Any]]


@dataclass
class Worker:
    queue: ResearchQueue
    handlers: dict[str, Handler] = field(default_factory=dict)
    worker_id: str = field(default_factory=lambda: new_id("wkr"))
    processed: int = 0
    failed: int = 0

    def register(self, kind: str, handler: Handler) -> None:
        self.handlers[kind] = handler

    def run_once(self) -> dict[str, Any] | None:
        """Claim and process a single task. Returns the task dict or None if the queue empty."""
        task = self.queue.claim(self.worker_id)
        if task is None:
            return None
        handler = self.handlers.get(task["kind"])
        if handler is None:
            self.queue.fail(task["id"], self.worker_id, f"no handler for kind {task['kind']}")
            self.failed += 1
            return task

        def heartbeat(checkpoint: dict[str, Any]) -> bool:
            return self.queue.heartbeat(task["id"], self.worker_id, checkpoint=checkpoint)

        try:
            result = handler(task["payload"], task["checkpoint"], heartbeat)
            self.queue.complete(task["id"], self.worker_id, result)
            self.processed += 1
        except Exception as exc:  # noqa: BLE001 - convert to a durable failure
            self.queue.fail(task["id"], self.worker_id, f"{type(exc).__name__}: {exc}")
            self.failed += 1
        return task

    def drain(self, *, max_tasks: int = 100) -> int:
        """Process tasks until the queue is empty or ``max_tasks`` handled."""
        n = 0
        while n < max_tasks and self.run_once() is not None:
            n += 1
        return n
