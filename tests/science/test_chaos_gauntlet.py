"""Sprint 14 science test: the Persistent Runtime Chaos Gauntlet (12 scenarios)."""

from __future__ import annotations

from acero.benchmarks.chaos_gauntlet import run_chaos_gauntlet


def test_chaos_gauntlet_all_scenarios_survive():
    r = run_chaos_gauntlet()
    assert r["n"] == 12
    assert r["all_passed"], [k for k, c in r["cases"].items() if not c["passed"]]


def test_worker_crash_recovers():
    assert run_chaos_gauntlet()["cases"]["1_worker_crash"]["passed"]


def test_duplicate_worker_blocked():
    assert run_chaos_gauntlet()["cases"]["2_duplicate_worker"]["passed"]


def test_replay_blocked_cross_and_in_process():
    assert run_chaos_gauntlet()["cases"]["5_replay"]["passed"]


def test_restart_preserves_checkpoint():
    assert run_chaos_gauntlet()["cases"]["6_restart"]["passed"]


def test_partial_output_escalates_to_human():
    c = run_chaos_gauntlet()["cases"]["8_partial_output"]
    assert c["decision"] == "HUMAN_REVIEW"
