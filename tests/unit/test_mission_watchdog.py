"""Watchdog self-heal for stuck missions (the 90%-forever bug): a mission whose worker
vanished must be re-submitted; one hung far past grace must be force-failed; a live,
legitimately-slow step must be left alone."""

from __future__ import annotations

from acero.portal.missions import (
    REAP_HUNG_SEC,
    STALE_HEARTBEAT_SEC,
    _stale_action,
)

NOW = 10_000.0


def test_worker_gone_and_stale_is_resumed():
    hb = NOW - (STALE_HEARTBEAT_SEC + 60)
    assert _stale_action("RUNNING", hb, in_active=False, now=NOW) == "resume"


def test_worker_gone_but_fresh_is_left_alone():
    hb = NOW - 10          # died just now; give it a beat before resuming
    assert _stale_action("RUNNING", hb, in_active=False, now=NOW) is None


def test_live_slow_step_is_not_touched():
    # worker present (in _ACTIVE), heartbeat stale because the step is long but alive
    hb = NOW - (STALE_HEARTBEAT_SEC + 300)
    assert _stale_action("RUNNING", hb, in_active=True, now=NOW) is None


def test_hung_worker_past_grace_is_reaped():
    hb = NOW - (REAP_HUNG_SEC + 60)
    assert _stale_action("RUNNING", hb, in_active=True, now=NOW) == "reap"


def test_finished_missions_are_never_acted_on():
    hb = NOW - 100_000
    for status in ("DONE", "FAILED", "PENDING", "COMPLETE"):
        assert _stale_action(status, hb, in_active=False, now=NOW) is None


def test_missing_heartbeat_treated_as_stale_when_worker_gone():
    assert _stale_action("RUNNING", 0.0, in_active=False, now=NOW) == "resume"
