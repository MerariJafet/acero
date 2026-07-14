"""Local experiment scheduler (Sprint 7.3).

A safe, in-process queue with:
  * concurrency limit (ThreadPoolExecutor),
  * per-task wall-clock timeout,
  * retries with a retry budget,
  * priority ordering,
  * cancellation,
  * an on_state callback for checkpointing/persistence (=> recovery after restart),
  * partial-failure isolation (one task failing does not kill the batch).

No distributed infrastructure. Task functions should honour ``stop`` (a threading
Event) for cooperative cancellation; the sandbox backends also enforce their own
hard timeouts on the underlying process.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    RETRYABLE = "RETRYABLE"


@dataclass
class Task:
    id: str
    fn: Callable[[threading.Event], dict[str, Any]]
    priority: float = 0.5           # higher runs first
    timeout_sec: float = 30.0
    max_retries: int = 1


@dataclass
class TaskResult:
    id: str
    state: TaskState
    attempts: int
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_sec: float = 0.0


@dataclass
class LocalScheduler:
    concurrency: int = 4
    on_state: Callable[[str, TaskState, TaskResult | None], None] | None = None
    _cancelled: set[str] = field(default_factory=set)
    _stops: dict[str, threading.Event] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def cancel(self, task_id: str) -> None:
        with self._lock:
            self._cancelled.add(task_id)
            ev = self._stops.get(task_id)
        if ev is not None:
            ev.set()

    def _emit(self, task_id: str, state: TaskState, result: TaskResult | None = None) -> None:
        if self.on_state:
            self.on_state(task_id, state, result)

    def _run_one(self, task: Task) -> TaskResult:
        with self._lock:
            if task.id in self._cancelled:
                res = TaskResult(task.id, TaskState.CANCELLED, attempts=0)
                self._emit(task.id, TaskState.CANCELLED, res)
                return res
        attempts = 0
        last_error: str | None = None
        while attempts <= task.max_retries:
            attempts += 1
            with self._lock:
                if task.id in self._cancelled:
                    res = TaskResult(task.id, TaskState.CANCELLED, attempts=attempts - 1)
                    self._emit(task.id, TaskState.CANCELLED, res)
                    return res
            stop = threading.Event()
            with self._lock:
                self._stops[task.id] = stop
            self._emit(task.id, TaskState.RUNNING)
            start = time.monotonic()
            inner = ThreadPoolExecutor(max_workers=1)
            fut: Future = inner.submit(task.fn, stop)
            try:
                value = fut.result(timeout=task.timeout_sec)
                dur = time.monotonic() - start
                res = TaskResult(task.id, TaskState.COMPLETED, attempts, result=value,
                                 duration_sec=round(dur, 4))
                self._emit(task.id, TaskState.COMPLETED, res)
                inner.shutdown(wait=False)
                return res
            except TimeoutError:
                stop.set()
                last_error = f"timeout after {task.timeout_sec}s"
                inner.shutdown(wait=False)
                if attempts > task.max_retries:
                    res = TaskResult(task.id, TaskState.TIMEOUT, attempts, error=last_error)
                    self._emit(task.id, TaskState.TIMEOUT, res)
                    return res
                self._emit(task.id, TaskState.RETRYABLE)
            except Exception as exc:  # noqa: BLE001 - isolate task failure
                last_error = f"{type(exc).__name__}: {exc}"
                inner.shutdown(wait=False)
                if attempts > task.max_retries:
                    res = TaskResult(task.id, TaskState.FAILED, attempts, error=last_error)
                    self._emit(task.id, TaskState.FAILED, res)
                    return res
                self._emit(task.id, TaskState.RETRYABLE)
        res = TaskResult(task.id, TaskState.FAILED, attempts, error=last_error)
        self._emit(task.id, TaskState.FAILED, res)
        return res

    def run(self, tasks: list[Task], skip_ids: set[str] | None = None) -> dict[str, TaskResult]:
        """Run tasks (highest priority first) with the configured concurrency.

        ``skip_ids`` supports RESUME: already-COMPLETED task ids are not re-run.
        """
        skip_ids = skip_ids or set()
        pending = sorted([t for t in tasks if t.id not in skip_ids],
                         key=lambda t: t.priority, reverse=True)
        results: dict[str, TaskResult] = {}
        with ThreadPoolExecutor(max_workers=max(1, self.concurrency)) as pool:
            futs = {pool.submit(self._run_one, t): t for t in pending}
            for fut in futs:
                r = fut.result()
                results[r.id] = r
        return results
