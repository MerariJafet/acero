"""Sprint 19 science test: the External Review Preparation Gauntlet."""

from __future__ import annotations

from acero.benchmarks.external_review_gauntlet import run_external_review_gauntlet


def test_external_review_gauntlet_all_pass(tmp_path, disc_store):
    r = run_external_review_gauntlet(str(tmp_path), disc_store)
    assert r["n"] >= 10
    assert r["all_passed"], [k for k, c in r["cases"].items() if not c["passed"]]


def test_wrong_version_review_blocked(tmp_path, disc_store):
    assert run_external_review_gauntlet(str(tmp_path), disc_store)["cases"]["3_wrong_version"]["blocked"]


def test_ai_authorship_blocked(tmp_path, disc_store):
    c = run_external_review_gauntlet(str(tmp_path), disc_store)["cases"]["9_ai_authorship_blocked"]
    assert c["ai_listed_as_author"] is False


def test_incompatible_license_blocks_bundle(tmp_path, disc_store):
    assert run_external_review_gauntlet(str(tmp_path), disc_store)["cases"]["8_incompatible_license"]["blocked"]
