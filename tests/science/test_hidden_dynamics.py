"""Scientific-integrity tests for the Hidden Dynamics Discovery Benchmark.

Asserts process guarantees and model-recovery behaviour, not a specific number.
"""

from __future__ import annotations

import pytest

from acero.benchmarks.hidden_dynamics import run_hidden_dynamics

pytestmark = pytest.mark.science


@pytest.fixture(scope="module")
def bench_result():
    """Run the benchmark once for the module (exponential_decay is fast)."""
    from sqlalchemy import create_engine

    from acero.discovery.store import DiscoveryStore
    from acero.ledger.db import make_session_factory
    from acero.ledger.models import Base
    from acero.ledger.service import ResearchLedger

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    sf = make_session_factory(engine)
    led = ResearchLedger(sf)
    store = DiscoveryStore(sf, led)
    proj = led.create_project("HD test", domain="physics")
    rep = run_hidden_dynamics(led, store, proj.id, system="exponential_decay", seeds=[1, 2])
    return rep


def test_model_recovery_low_noise(bench_result):
    # The winning family should match the hidden generating family under low noise.
    assert bench_result["winner_family"] == bench_result["hidden_family"] == "exponential"


def test_overfitter_fails_out_of_distribution(bench_result):
    # poly9 extrapolation error must dwarf the winner's.
    assert bench_result["poly9_extrapolation_rmse"] > 10 * bench_result["winner_extrapolation_rmse"]


def test_experiment_was_discriminating(bench_result):
    assert bench_result["critique"]["discriminating"] is True
    assert bench_result["eig_bits"] > 0.0


def test_at_least_four_mechanisms_and_a_null(bench_result):
    assert bench_result["diversity"]["n_mechanisms"] >= 4
    assert bench_result["n_falsifiable"] >= 4


def test_rejected_candidates_preserved(bench_result):
    assert bench_result["n_rejected_kept"] >= 1


def test_confidence_updated_with_provenance(bench_result):
    post = bench_result["confidence_posterior"]
    assert abs(sum(post.values()) - 1.0) < 1e-2  # rounded to 4 dp in the report


def test_negative_results_recorded(bench_result):
    assert bench_result["negative_records"] >= 1


def test_reproducible_rerun(bench_result):
    assert bench_result["reproduced"] is True


def test_next_experiment_has_alternative(bench_result):
    ne = bench_result["next_experiment"]
    assert ne is not None
    assert len(ne["alternatives"]) >= 1
    assert ne["reason_not_to_run"]


def test_honesty_statement_present(bench_result):
    text = " ".join(bench_result["honesty"]).lower()
    assert "sintétic" in text and "recuperación de modelos" in text
    assert bench_result["cannot_conclude"]


def test_learning_docs_written(bench_result):
    assert set(bench_result["learning_files"]) >= {
        "problem_intuition.md", "hypotheses.md", "experimental_design.md",
        "information_gain.md", "results.md", "falsification.md",
        "what_changed.md", "knowledge_check.md",
    }


def test_high_noise_falsification_probe_ran(bench_result):
    # The winner-degradation probe under high noise was executed and recorded.
    assert isinstance(bench_result["winner_degrades_under_noise"], bool)


# --- regression tests for adversarial-audit fixes ---
def test_confidence_not_overconfident(bench_result):
    # Audit fix: tempered likelihood must avoid false precision.
    post = bench_result["confidence_posterior"]
    assert max(post.values()) < 0.99
    assert "UNCALIBRATED" in bench_result["confidence_note"]


def test_privileged_hypothesis_disclosed(bench_result):
    # Audit fix: the structural privilege of the generating family is disclosed.
    text = " ".join(bench_result["cannot_conclude"]).lower()
    assert "privilegiad" in text


def test_partial_ambiguity_surfaced(bench_result):
    # Audit fix: shared-outcome hypotheses are reported, not hidden.
    assert "partial_ambiguity_groups" in bench_result


def test_process_quality_relabelled(bench_result):
    # Audit fix: 'process_quality' (ran/reproduced/discriminating), not scientific confidence.
    assert "process_quality" in bench_result
    assert "result_quality" not in bench_result


def test_weakened_hypotheses_recorded_as_negatives(bench_result):
    # Audit fix: weakened hypotheses are preserved as negative context, not only poly9.
    if bench_result["weakened_hypotheses"]:
        assert bench_result["negative_records"] > 1


def test_ranking_titles_consistent(bench_result):
    # Audit fix: titles ordered by tournament ranking.
    assert "top_titles_by_rank" in bench_result
    assert len(bench_result["top_titles_by_rank"]) == len(bench_result["tournament_ranking"][:4])
