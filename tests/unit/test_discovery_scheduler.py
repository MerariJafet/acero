"""Sprint 7 tests: local scheduler."""

from __future__ import annotations

import threading
import time

from acero.discovery.scheduler import LocalScheduler, Task, TaskState


def _ok(value):
    def fn(stop):
        return {"value": value}
    return fn


def test_runs_all_tasks_and_reports_state():
    states = []
    sched = LocalScheduler(concurrency=3, on_state=lambda tid, st, r: states.append((tid, st)))
    tasks = [Task(id=f"t{i}", fn=_ok(i)) for i in range(5)]
    results = sched.run(tasks)
    assert len(results) == 5
    assert all(r.state == TaskState.COMPLETED for r in results.values())
    assert any(st == TaskState.RUNNING for _, st in states)
    assert results["t2"].result == {"value": 2}


def test_concurrency_actually_parallel():
    barrier = threading.Barrier(3, timeout=5)

    def fn(stop):
        barrier.wait()  # only completes if 3 run at once
        return {"ok": True}

    sched = LocalScheduler(concurrency=3)
    results = sched.run([Task(id=f"t{i}", fn=fn, timeout_sec=5) for i in range(3)])
    assert all(r.state == TaskState.COMPLETED for r in results.values())


def test_timeout_marks_task():
    def slow(stop):
        for _ in range(100):
            if stop.is_set():
                return {"stopped": True}
            time.sleep(0.05)
        return {"done": True}

    sched = LocalScheduler(concurrency=1)
    results = sched.run([Task(id="slow", fn=slow, timeout_sec=0.2, max_retries=0)])
    assert results["slow"].state == TaskState.TIMEOUT


def test_retry_then_fail():
    calls = {"n": 0}

    def flaky(stop):
        calls["n"] += 1
        raise RuntimeError("boom")

    sched = LocalScheduler(concurrency=1)
    results = sched.run([Task(id="f", fn=flaky, max_retries=2)])
    assert results["f"].state == TaskState.FAILED
    assert results["f"].attempts == 3  # 1 + 2 retries
    assert calls["n"] == 3


def test_retry_then_success():
    calls = {"n": 0}

    def eventually(stop):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("first fails")
        return {"ok": True}

    sched = LocalScheduler(concurrency=1)
    results = sched.run([Task(id="e", fn=eventually, max_retries=2)])
    assert results["e"].state == TaskState.COMPLETED
    assert results["e"].attempts == 2


def test_cancellation():
    sched = LocalScheduler(concurrency=1)
    sched.cancel("c")
    results = sched.run([Task(id="c", fn=_ok(1))])
    assert results["c"].state == TaskState.CANCELLED


def test_partial_failure_isolated():
    def boom(stop):
        raise ValueError("x")

    sched = LocalScheduler(concurrency=2)
    results = sched.run([Task(id="ok", fn=_ok(1), max_retries=0),
                         Task(id="bad", fn=boom, max_retries=0)])
    assert results["ok"].state == TaskState.COMPLETED
    assert results["bad"].state == TaskState.FAILED


def test_resume_skips_completed():
    # Simulate a restart: 't0' already completed, resume must skip it.
    ran = []
    sched = LocalScheduler(concurrency=2)

    def _track(tid):
        def fn(stop):
            ran.append(tid)
            return {"tid": tid}
        return fn

    tasks = [Task(id="t0", fn=_track("t0")), Task(id="t1", fn=_track("t1"))]
    results = sched.run(tasks, skip_ids={"t0"})
    assert "t1" in results and "t0" not in results
    assert ran == ["t1"]
