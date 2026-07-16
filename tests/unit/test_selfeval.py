"""Sprint 18 tests: capability/benchmark registries, baseline, regression, failures, prompts."""

from __future__ import annotations

import pytest

from acero.selfeval import prompts
from acero.selfeval.benchmarks import definitions, run_one
from acero.selfeval.capabilities import default_capabilities
from acero.selfeval.codex_drift import detect_drift, fingerprint
from acero.selfeval.engine import run_evaluation
from acero.selfeval.failures import FailureMemory
from acero.selfeval.models import (
    CapabilityStatus,
    ImprovementProposal,
    RegressionStatus,
)
from acero.selfeval.proposals import ProposalError, ProposalRegistry
from acero.selfeval.regression import compare_benchmark, compare_metric, compare_run
from acero.selfeval.tools import evaluate_tools

# --- capabilities ---------------------------------------------------------

def test_capability_registry_covers_required_capabilities():
    names = {c.name for c in default_capabilities()}
    for required in ("governing_structure_inference", "calibration", "abstention",
                     "publication_readiness", "astronomy_timeseries_analysis"):
        assert required in names


def test_astronomy_capability_is_experimental_not_supported():
    astro = next(c for c in default_capabilities()
                 if c.name == "astronomy_timeseries_analysis")
    assert astro.status == CapabilityStatus.EXPERIMENTAL
    assert astro.limitations


# --- benchmark runner -----------------------------------------------------

def test_benchmark_runner_records_provenance():
    r = run_one("mutation")
    assert r["passed"] and "commit" in r and "environment" in r and r["duration_sec"] >= 0


def test_benchmark_definitions_have_thresholds():
    for d in definitions():
        assert d.acceptance_thresholds       # every benchmark has a pre-registered threshold


def test_unknown_benchmark_raises():
    with pytest.raises(KeyError):
        run_one("nope")


# --- baseline locking -----------------------------------------------------

def test_baseline_write_load_and_tamper_detection(tmp_path, monkeypatch):
    import acero.selfeval.baseline as bl
    monkeypatch.setattr(bl, "_dir", lambda v: tmp_path / v)
    results = {"results": {"x": {"metrics": {"pass_rate": 1.0}}}}
    bl.write("vT", results)
    assert bl.load("vT") == results
    # tamper with the file → signature/hash mismatch detected
    (tmp_path / "vT" / "results.json").write_text('{"results": {"x": {"metrics": {}}}}')
    with pytest.raises(bl.BaselineError):
        bl.load("vT")


def test_baseline_refuses_silent_overwrite(tmp_path, monkeypatch):
    import acero.selfeval.baseline as bl
    monkeypatch.setattr(bl, "_dir", lambda v: tmp_path / v)
    bl.write("vT", {"results": {}})
    with pytest.raises(bl.BaselineError):
        bl.write("vT", {"results": {}})        # no force → refused
    bl.write("vT", {"results": {}}, force=True)  # explicit force ok


# --- regression detection -------------------------------------------------

def test_compare_metric_tolerance_and_direction():
    assert compare_metric("pass_rate", 1.0, 1.0) == RegressionStatus.UNCHANGED
    assert compare_metric("pass_rate", 1.0, 0.9) == RegressionStatus.REGRESSED
    assert compare_metric("recovery_rate", 0.8, 0.83) == RegressionStatus.UNCHANGED  # within tol
    # duration: lower is better
    assert compare_metric("duration_sec", 1.0, 5.0) == RegressionStatus.REGRESSED
    assert compare_metric("duration_sec", 5.0, 1.0) == RegressionStatus.IMPROVED


def test_compare_run_flags_regression():
    base = {"results": {"b": {"metrics": {"pass_rate": 1.0}}}}
    cur = {"results": {"b": {"metrics": {"pass_rate": 0.5}}}}
    r = compare_run(base, cur)
    assert r["has_regression"] and "b" in r["regressions"]


def test_compare_benchmark_insufficient_without_baseline():
    r = compare_benchmark(None, {"metrics": {"x": 1.0}})
    assert r["status"] == RegressionStatus.INSUFFICIENT_DATA.value


# --- failure memory -------------------------------------------------------

def test_failure_memory_seeds_real_failures_with_tests(disc_store):
    fm = FailureMemory(disc_store)
    fm.seed()
    cats = fm.by_category()
    assert "statistical" in cats and "security" in cats
    # every seeded FIXED failure has a regression test
    assert fm.without_regression_test() == []


def test_failure_memory_seed_is_idempotent(disc_store):
    fm = FailureMemory(disc_store)
    n1 = fm.seed()
    n2 = fm.seed()
    assert n1 > 0 and n2 == 0


# --- improvement proposals ------------------------------------------------

def test_proposal_requires_evidence_and_rollback(disc_store):
    reg = ProposalRegistry(disc_store)
    with pytest.raises(ProposalError):
        reg.propose(ImprovementProposal(problem="x", rollback_plan="revert"))  # no evidence
    with pytest.raises(ProposalError):
        reg.propose(ImprovementProposal(problem="x", evidence=["e"]))          # no rollback
    ok = reg.propose(ImprovementProposal(problem="x", evidence=["e"],
                                         rollback_plan="revert commit"))
    assert ok.human_decision == "pending"


# --- prompt evaluation ----------------------------------------------------

def test_prompt_eval_fails_unsafe_and_overclaiming():
    r = prompts.run()
    scores = {s["prompt_version"]: s for s in r["scores"]}
    assert scores["v1-UNSAFE"]["unsafe"] and not scores["v1-UNSAFE"]["passed"]
    assert scores["v1-BAD"]["unsupported_claims"] and not scores["v1-BAD"]["passed"]


# --- codex drift ----------------------------------------------------------

def test_codex_drift_flags_change():
    fp = fingerprint()
    assert detect_drift(None)["status"] == "BASELINE_RECORDED"
    changed = {**fp, "codex_present": not fp["codex_present"]}
    assert detect_drift(changed)["revalidate"] is True


# --- tool evaluation ------------------------------------------------------

def test_tool_evaluation_empty_is_honest(disc_store, project):
    r = evaluate_tools(disc_store, project.id)
    assert r["n_tools"] == 0 and r["degraded"] == []


# --- engine ---------------------------------------------------------------

def test_engine_never_auto_promotes_experimental(monkeypatch):
    r = run_evaluation()
    astro = next(c for c in r["capabilities"]
                 if c["name"] == "astronomy_timeseries_analysis")
    # even though its benchmark passes, it stays EXPERIMENTAL (no self-promotion)
    assert astro["status"] == "EXPERIMENTAL"


def test_engine_reports_no_self_approval():
    r = run_evaluation()
    assert "never self-approves" in r["note"]
    assert r["verdict"] in ("NO_REGRESSION", "REGRESSION_DETECTED")
