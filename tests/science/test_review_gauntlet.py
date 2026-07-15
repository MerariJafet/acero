"""Sprint 12 science test: the Human Scientific Review Gauntlet."""

from __future__ import annotations

from acero.benchmarks.review_gauntlet import run_review_gauntlet


def test_review_gauntlet_all_pass(tmp_path):
    r = run_review_gauntlet(str(tmp_path / "g"))
    assert r["n"] == 6
    assert r["all_passed"], [k for k, c in r["cases"].items() if not c["passed"]]


def test_unreviewed_export_blocked(tmp_path):
    assert run_review_gauntlet(str(tmp_path / "g"))["cases"]["1_not_reviewed"]["blocked"]


def test_not_ready_export_blocked(tmp_path):
    assert run_review_gauntlet(str(tmp_path / "g"))["cases"]["2_not_ready"]["blocked"]


def test_ai_reviewer_refused(tmp_path):
    c = run_review_gauntlet(str(tmp_path / "g"))["cases"]["4_ai_reviewer"]
    assert c["review_refused"] and c["export_blocked"]


def test_approved_export_never_auto_publishes(tmp_path):
    c = run_review_gauntlet(str(tmp_path / "g"))["cases"]["6_approved_local_export"]
    assert c["exported"] and c["auto_published"] is False
