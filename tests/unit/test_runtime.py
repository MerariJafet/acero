"""Sprint 14 tests: persistent queue, leases, recovery, idempotency, secrets, tokens."""

from __future__ import annotations

import os

from sqlalchemy import create_engine

from acero.ledger.db import make_session_factory
from acero.ledger.models import Base
from acero.runtime.queue import ResearchQueue
from acero.runtime.recovery import RecoveryDecision, decide
from acero.runtime.secrets import (
    generate_secret,
    get_secret,
    redact,
    secret_status,
)
from acero.runtime.store import RuntimeStore
from acero.runtime.worker import Worker


def _sf():
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    return make_session_factory(eng)


def _queue(lease=30):
    return ResearchQueue(_sf(), lease_seconds=lease)


# --- queue + leases -------------------------------------------------------

def test_enqueue_and_claim():
    q = _queue()
    q.enqueue("t1", "compute", priority=0.9)
    q.enqueue("t2", "compute", priority=0.1)
    first = q.claim("w1")
    assert first["id"] == "t1"                       # highest priority first


def test_second_worker_cannot_steal_active_lease():
    q = _queue()
    q.enqueue("t1", "compute")
    assert q.claim("w1") is not None
    assert q.claim("w2") is None                     # leased, not expired


def test_expired_lease_is_reclaimable():
    q = _queue(lease=0)
    q.enqueue("t1", "compute")
    q.claim("w1")
    assert q.reap_expired() == ["t1"]
    assert q.claim("w2") is not None                 # resumed by another worker


def test_heartbeat_persists_checkpoint_and_renews():
    q = _queue()
    q.enqueue("t1", "compute")
    q.claim("w1")
    assert q.heartbeat("t1", "w1", checkpoint={"done": 2})
    assert q.store.get_task("t1")["checkpoint"] == {"done": 2}


def test_foreign_heartbeat_rejected():
    q = _queue()
    q.enqueue("t1", "compute")
    q.claim("w1")
    assert q.heartbeat("t1", "w2") is False


def test_complete_requires_lease_owner():
    q = _queue()
    q.enqueue("t1", "compute")
    q.claim("w1")
    assert q.complete("t1", "w2", {"r": 1}) is False
    assert q.complete("t1", "w1", {"r": 1}) is True
    assert q.store.get_task("t1")["status"] == "DONE"


def test_fail_retries_then_dead_letters():
    q = _queue()
    q.enqueue("t1", "compute", max_attempts=2)
    q.claim("w1")
    assert q.fail("t1", "w1", "boom") == "RETRY"
    q.claim("w1")
    assert q.fail("t1", "w1", "boom again") == "DEAD_LETTER"
    assert q.store.get_task("t1")["status"] == "DEAD_LETTER"


def test_cancel_makes_task_unclaimable():
    q = _queue()
    q.enqueue("t1", "compute")
    assert q.cancel("t1")
    assert q.claim("w1") is None


# --- idempotency ----------------------------------------------------------

def test_idempotent_enqueue_dedups():
    q = _queue()
    a = q.enqueue("t1", "ingest", idempotency_key="ds-hash-1")
    b = q.enqueue("t2", "ingest", idempotency_key="ds-hash-1")
    assert a["id"] == b["id"] == "t1"                # second is a no-op returning the first


# --- cross-process token spend --------------------------------------------

def test_token_spend_is_single_use_across_process():
    store = RuntimeStore(_sf())
    store.record_token("tok1", "update_belief", "p")
    assert store.spend_token("tok1") is True
    assert store.spend_token("tok1") is False        # replay blocked at the DB layer


# --- recovery decisions ---------------------------------------------------

def test_recovery_resume_with_checkpoint():
    assert decide({"attempts": 1, "max_attempts": 3, "checkpoint": {"i": 2}}) \
        == RecoveryDecision.RESUME


def test_recovery_retry_without_checkpoint():
    assert decide({"attempts": 1, "max_attempts": 3, "checkpoint": {}}) \
        == RecoveryDecision.RETRY


def test_recovery_rollback_on_partial_mutation():
    assert decide({"attempts": 1, "max_attempts": 3, "checkpoint": {},
                   "partial_mutation": True}) == RecoveryDecision.ROLLBACK


def test_recovery_dead_letter_when_exhausted():
    assert decide({"attempts": 3, "max_attempts": 3, "checkpoint": {}}) \
        == RecoveryDecision.DEAD_LETTER


def test_recovery_human_review_on_inconsistency():
    assert decide({"attempts": 1, "max_attempts": 3}, artifact_present=True,
                  record_present=False) == RecoveryDecision.HUMAN_REVIEW


# --- worker ---------------------------------------------------------------

def test_worker_processes_task_end_to_end():
    q = _queue()
    q.enqueue("t1", "double", payload={"x": 21})
    w = Worker(q)
    w.register("double", lambda p, c, hb: {"y": p["x"] * 2})
    w.run_once()
    task = q.store.get_task("t1")
    assert task["status"] == "DONE" and task["result"] == {"y": 42}


def test_worker_failure_becomes_durable_not_crash():
    q = _queue()
    q.enqueue("t1", "boom")
    w = Worker(q)
    w.register("boom", lambda p, c, hb: (_ for _ in ()).throw(RuntimeError("x")))
    w.run_once()
    assert q.store.get_task("t1")["status"] in ("QUEUED", "DEAD_LETTER")
    assert q.store.get_task("t1")["error"]


def test_restart_sees_persisted_state():
    sf = _sf()
    q = ResearchQueue(sf)
    q.enqueue("t1", "compute")
    q.claim("w1")
    q.heartbeat("t1", "w1", checkpoint={"done": 3})
    q2 = ResearchQueue(sf)                           # "restart": new object, same DB
    assert q2.store.get_task("t1")["checkpoint"] == {"done": 3}


# --- secrets --------------------------------------------------------------

def test_generate_secret_is_hex_and_redacts():
    key_id, hex_secret = generate_secret()
    assert key_id.startswith("key-") and len(hex_secret) == 64
    assert "…" in redact(hex_secret) and hex_secret not in redact(hex_secret)


def test_dev_mode_has_ephemeral_secret():
    os.environ.pop("ACERO_HMAC_SECRET", None)
    os.environ.pop("ACERO_ENV", None)
    s = secret_status()
    assert s["mode"] == "development" and s["configured"] is False
    kid, secret = get_secret()
    assert kid.startswith("dev-") and len(secret) == 32


def test_env_secret_is_used_when_present():
    os.environ["ACERO_HMAC_SECRET"] = "deadbeef" * 4
    try:
        s = secret_status()
        assert s["configured"] is True
        _, secret = get_secret()
        assert len(secret) == 32
    finally:
        os.environ.pop("ACERO_HMAC_SECRET", None)
