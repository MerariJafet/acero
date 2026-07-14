"""Sprint 9 science test: the Human-in-the-Loop Scientific Understanding Benchmark."""

from __future__ import annotations

from acero.benchmarks.human_understanding import run_human_understanding


def test_benchmark_runs_and_reports_all_cases():
    r = run_human_understanding()
    assert set(r) == {"case_1_sindy", "case_2_analogy", "case_3_sunspots",
                      "case_4_adversarial_gate", "transfer", "prediction"}


def test_case1_distinguishes_fit_and_blocks_novelty():
    r = run_human_understanding()["case_1_sindy"]
    assert r["concept_status"] in ("CONCEPTUALLY_UNDERSTOOD", "PROCEDURALLY_COMPETENT")
    assert r["misconception_detected"]         # the 'law' misconception is caught
    assert r["novelty_blocked"]                # can't claim novelty without transfer


def test_case2_rejects_full_equivalence():
    r = run_human_understanding()["case_2_analogy"]
    assert r["rejects_equivalence"]
    assert not r["false_equivalence_flagged"]  # negation not a false positive


def test_case3_periodicity_is_not_mechanism():
    r = run_human_understanding()["case_3_sunspots"]
    assert r["distinguishes_pattern_mechanism"]
    assert "mechanism_vs_pattern" in r["misconception_on_bad_claim"]


def test_case4_adversarial_report_is_blocked():
    r = run_human_understanding()["case_4_adversarial_gate"]
    assert r["gate_blocked"]
    assert r["n_blockers"] >= 4
    assert r["human_detected_score"] >= 0.8    # human can detect the flaws


def test_transfer_pass_and_wrong_answer_flagged():
    r = run_human_understanding()["transfer"]
    assert r["transfer_pass"]
    assert r["wrong_answer_flagged"]


def test_prediction_locked_and_overconfidence_detected():
    r = run_human_understanding()["prediction"]
    assert r["locked"]
    assert r["comparison"] == "incorrect"
    assert r["overconfident"]
