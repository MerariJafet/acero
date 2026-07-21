"""Sprint 23 auth unit tests: hashing, sessions, CSRF, rate limiting."""

from __future__ import annotations

import pytest

from acero.portal.auth import (
    RateLimiter,
    SessionManager,
    UserStore,
    hash_password,
    verify_password,
)


def test_password_never_stored_plain(tmp_path):
    store = UserStore(tmp_path / "u.json")
    store.create_user("alice", "correcthorse")
    raw = (tmp_path / "u.json").read_text()
    assert "correcthorse" not in raw
    assert "pbkdf2$" in raw


def test_hash_verify_roundtrip():
    h = hash_password("hunter2xx")
    assert verify_password("hunter2xx", h)
    assert not verify_password("wrong", h)


def test_short_password_rejected():
    with pytest.raises(ValueError):
        hash_password("short")


def test_user_verify(tmp_path):
    store = UserStore(tmp_path / "u.json")
    store.create_user("bob", "password123")
    assert store.verify("bob", "password123")
    assert not store.verify("bob", "nope")
    assert not store.verify("ghost", "whatever")   # unknown user, no crash


def test_no_duplicate_user(tmp_path):
    store = UserStore(tmp_path / "u.json")
    store.create_user("bob", "password123")
    with pytest.raises(ValueError):
        store.create_user("bob", "another12")
    store.create_user("bob", "another12", overwrite=True)   # explicit overwrite ok


def test_session_lifecycle():
    sm = SessionManager(ttl_s=100)
    s = sm.create("alice", now=0.0)
    assert sm.get(s.sid, now=50.0) is not None
    assert sm.get(s.sid, now=200.0) is None          # expired
    s2 = sm.create("alice", now=0.0)
    sm.invalidate(s2.sid)
    assert sm.get(s2.sid, now=1.0) is None


def test_session_csrf_is_separate_from_sid():
    sm = SessionManager()
    s = sm.create("alice")
    assert s.csrf and s.csrf != s.sid


def test_sessions_persist_across_restart(tmp_path):
    path = tmp_path / "sessions.json"
    sm = SessionManager(persist_path=path)
    s = sm.create("merari")
    # a NEW manager (simulating a portal restart) loads the same session
    sm2 = SessionManager(persist_path=path)
    assert sm2.get(s.sid) is not None
    assert sm2.get(s.sid).user == "merari"
    # invalidation persists too
    sm2.invalidate(s.sid)
    sm3 = SessionManager(persist_path=path)
    assert sm3.get(s.sid) is None


def test_expired_sessions_not_loaded(tmp_path):
    path = tmp_path / "s.json"
    sm = SessionManager(ttl_s=0.0, persist_path=path)
    s = sm.create("bob", now=0.0)
    sm2 = SessionManager(persist_path=path)
    assert sm2.get(s.sid, now=100.0) is None


def test_rate_limiter_locks_after_failures():
    rl = RateLimiter(max_attempts=3, window_s=100, lockout_s=100)
    for _ in range(3):
        assert rl.check("k", now=0.0)
        rl.record_failure("k", now=0.0)
    assert not rl.check("k", now=1.0)               # locked out
    assert rl.retry_after("k", now=1.0) > 0
    assert rl.check("k", now=200.0)                 # lockout window passed


def test_rate_limiter_reset_on_success():
    rl = RateLimiter(max_attempts=3)
    rl.record_failure("k", now=0.0)
    rl.record_success("k")
    assert rl.check("k", now=1.0)
