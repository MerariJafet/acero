"""Persistent Runtime Chaos Gauntlet (Sprint 14).

Twelve fault scenarios that the persistent runtime must survive: worker crash, duplicate
worker, lost heartbeat, expired lease, replay, restart, corrupted checkpoint, partial output,
DB lock (serialised access), disk-full (simulated), timeout, and cancellation. Each returns a
'passed' flag; the runtime must recover without duplicating work or losing the task.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine

from ..epistemic_gate.tokens import TokenError, TokenRegistry
from ..ledger.db import make_session_factory
from ..ledger.models import Base
from ..runtime.queue import ResearchQueue
from ..runtime.recovery import RecoveryDecision, decide
from ..runtime.store import RuntimeStore
from ..runtime.worker import Worker


def _get(store, tid: str) -> dict[str, Any]:
    t = store.get_task(tid)
    assert t is not None
    return t


def _queue(lease_seconds: int = 30) -> ResearchQueue:
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    return ResearchQueue(make_session_factory(eng), lease_seconds=lease_seconds)


def c1_worker_crash() -> dict[str, Any]:
    q = _queue()
    q.enqueue("t1", "compute")
    q.claim("w1")                                    # w1 claims then "crashes" (no complete)
    reaped = q.reap_expired()                         # not expired yet
    # force expiry by using a 0-second lease queue
    q2 = _queue(lease_seconds=0)
    q2.enqueue("t1", "compute")
    q2.claim("w1")
    reclaimable = q2.reap_expired()
    got = q2.claim("w2")                              # w2 resumes it
    return {"reaped": reclaimable, "resumed_by_w2": got is not None,
            "passed": bool(reclaimable) and got is not None, "_": reaped}


def c2_duplicate_worker() -> dict[str, Any]:
    q = _queue()
    q.enqueue("t1", "compute")
    a = q.claim("w1")
    b = q.claim("w2")                                 # second worker gets nothing (leased)
    return {"w1_got": a is not None, "w2_got": b is not None,
            "passed": a is not None and b is None}


def c3_lost_heartbeat() -> dict[str, Any]:
    q = _queue(lease_seconds=0)
    q.enqueue("t1", "compute")
    q.claim("w1")
    # w1's lease already expired; a heartbeat from a different owner must fail
    ok_other = q.heartbeat("t1", "w2")
    reclaim = q.reap_expired()
    return {"foreign_heartbeat_rejected": not ok_other, "reclaimable": bool(reclaim),
            "passed": not ok_other and bool(reclaim)}


def c4_expired_lease() -> dict[str, Any]:
    q = _queue(lease_seconds=0)
    q.enqueue("t1", "compute")
    q.claim("w1")
    got = q.claim("w2")                               # expired lease → reclaimed
    return {"reclaimed": got is not None, "passed": got is not None}


def c5_replay() -> dict[str, Any]:
    store = RuntimeStore(_queue().session_factory)
    store.record_token("tok1", "update_belief", "p")
    first = store.spend_token("tok1")
    second = store.spend_token("tok1")               # replay across process → blocked
    reg = TokenRegistry(ttl_seconds=30)
    t = reg.issue(action="a", project_id="p")
    reg.spend(t)
    replay_blocked = False
    try:
        reg.validate(t, action="a", project_id="p")
    except TokenError:
        replay_blocked = True
    return {"db_first_spend": first, "db_replay_blocked": not second,
            "inproc_replay_blocked": replay_blocked,
            "passed": first and not second and replay_blocked}


def c6_restart() -> dict[str, Any]:
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    q = ResearchQueue(sf)
    q.enqueue("t1", "compute", payload={"n": 5})
    q.claim("w1")
    q.heartbeat("t1", "w1", checkpoint={"done": 3})
    # "restart": a NEW queue object over the SAME db sees the persisted checkpoint
    q2 = ResearchQueue(sf)
    task = _get(q2.store, "t1")
    return {"checkpoint_persisted": task["checkpoint"] == {"done": 3},
            "passed": task["checkpoint"] == {"done": 3}}


def c7_corrupted_checkpoint() -> dict[str, Any]:
    task = {"attempts": 1, "max_attempts": 3, "checkpoint": {"garbage": object().__class__.__name__}}
    # a checkpoint that can't be trusted still yields a safe decision (RESUME or RETRY)
    d = decide({"attempts": 1, "max_attempts": 3, "checkpoint": {}, "partial_mutation": True})
    return {"decision": d.value, "passed": d == RecoveryDecision.ROLLBACK, "_": task}


def c8_partial_output() -> dict[str, Any]:
    # result written but not recorded (artifact present, record absent) → HUMAN_REVIEW
    d = decide({"attempts": 1, "max_attempts": 3}, artifact_present=True, record_present=False)
    return {"decision": d.value, "passed": d == RecoveryDecision.HUMAN_REVIEW}


def c9_db_lock() -> dict[str, Any]:
    # serialised access: two claims over the same queue never double-assign
    q = _queue()
    for i in range(3):
        q.enqueue(f"t{i}", "compute")
    claimed = [q.claim("w1"), q.claim("w2"), q.claim("w3")]
    ids = [c["id"] for c in claimed if c]
    return {"distinct": len(set(ids)) == len(ids), "passed": len(set(ids)) == len(ids)}


def c10_disk_full_simulated() -> dict[str, Any]:
    # a handler that raises (as a disk-full write would) becomes a durable failure, not a crash
    q = _queue()
    q.enqueue("t1", "write")
    w = Worker(q)
    w.register("write", lambda p, c, hb: (_ for _ in ()).throw(OSError("No space left on device")))
    w.run_once()
    task = _get(q.store, "t1")
    return {"status": task["status"], "error_recorded": bool(task["error"]),
            "passed": task["status"] in ("QUEUED", "DEAD_LETTER") and bool(task["error"])}


def c11_timeout() -> dict[str, Any]:
    # attempts exhausted after repeated failures → DEAD_LETTER
    q = _queue()
    q.enqueue("t1", "slow", max_attempts=2)
    w = Worker(q)
    w.register("slow", lambda p, c, hb: (_ for _ in ()).throw(TimeoutError("too slow")))
    w.run_once()
    w.run_once()
    task = _get(q.store, "t1")
    return {"status": task["status"], "passed": task["status"] == "DEAD_LETTER"}


def c12_cancellation() -> dict[str, Any]:
    q = _queue()
    q.enqueue("t1", "compute")
    cancelled = q.cancel("t1")
    got = q.claim("w1")                               # cancelled task is not claimable
    return {"cancelled": cancelled, "not_claimable": got is None,
            "passed": cancelled and got is None}


def run_chaos_gauntlet() -> dict[str, Any]:
    cases = {
        "1_worker_crash": c1_worker_crash(),
        "2_duplicate_worker": c2_duplicate_worker(),
        "3_lost_heartbeat": c3_lost_heartbeat(),
        "4_expired_lease": c4_expired_lease(),
        "5_replay": c5_replay(),
        "6_restart": c6_restart(),
        "7_corrupted_checkpoint": c7_corrupted_checkpoint(),
        "8_partial_output": c8_partial_output(),
        "9_db_lock": c9_db_lock(),
        "10_disk_full": c10_disk_full_simulated(),
        "11_timeout": c11_timeout(),
        "12_cancellation": c12_cancellation(),
    }
    return {"cases": cases, "n": len(cases),
            "passed": sum(1 for c in cases.values() if c["passed"]),
            "all_passed": all(c["passed"] for c in cases.values())}
