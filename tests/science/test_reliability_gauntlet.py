"""Sprint 11 science test: the Scientific Reliability Gauntlet (10 tracks)."""

from __future__ import annotations

from acero.benchmarks.reliability_gauntlet import run_gauntlet
from acero.reliability.domain_reliability import run_domain_reliability


def test_gauntlet_all_tracks_pass():
    r = run_gauntlet()
    assert r["n"] == 10
    assert r["all_passed"], [k for k, t in r["tracks"].items() if not t["passed"]]


def test_clean_pipeline_passes():
    assert run_gauntlet()["tracks"]["1_clean_pipeline"]["passed"]


def test_duplicate_evidence_counted_dependent():
    assert run_gauntlet()["tracks"]["2_duplicate_evidence"]["counted_as_dependent"]


def test_faulty_solver_blocked():
    assert run_gauntlet()["tracks"]["3_faulty_solver"]["blocked"]


def test_false_causality_blocked():
    assert run_gauntlet()["tracks"]["6_false_causality"]["blocked"]


def test_grader_gaming_fails():
    assert run_gauntlet()["tracks"]["7_grader_gaming"]["failed"]


def test_miscalibration_detected():
    assert run_gauntlet()["tracks"]["8_miscalibration"]["detected"]


def test_correct_abstention():
    assert run_gauntlet()["tracks"]["9_correct_abstention"]["abstains"]


def test_concurrent_bypass_all_blocked():
    t = run_gauntlet()["tracks"]["10_concurrent_bypass"]
    assert t["blocked"] == t["attempts"] == 8


def test_domain_reliability_all_pass():
    dr = run_domain_reliability()
    assert all(r["passed"] for r in dr.values()), \
        [d for d, r in dr.items() if not r["passed"]]
