"""P2: diagnose WHY cross-checks disagree so codegen variance can be told from genuine
scientific instability (accumulated across runs)."""
from __future__ import annotations

from acero.portal.experiment_factory import classify_disagreement, crosscheck_summary


def test_verdict_mismatch_with_matching_metrics_is_codegen_variance():
    a = {"verdict": "supports", "metrics": {"beta": 0.20, "p": 0.03}}
    b = {"verdict": "inconclusive", "metrics": {"beta": 0.205, "p": 0.031}}
    d = classify_disagreement(a, b)
    assert d["kind"] == "verdict_mismatch"
    assert d["metrics_agree_numerically"] is True
    assert d["likely_codegen_variance"] is True   # same numbers, different call


def test_metric_divergence_is_genuine_instability():
    a = {"verdict": "supports", "metrics": {"beta": 0.20}}
    b = {"verdict": "supports", "metrics": {"beta": 0.02}}   # 10x apart
    d = classify_disagreement(a, b)
    assert d["kind"] == "metric_divergence"
    assert "beta" in d["divergent_metrics"]
    assert d["likely_codegen_variance"] is False


def test_agree_case():
    a = {"verdict": "refutes", "metrics": {"x": 1.0}}
    d = classify_disagreement(a, {"verdict": "refutes", "metrics": {"x": 1.05}})
    assert d["kind"] == "agree"


def test_summary_aggregates_and_flags_variance():
    exps = [
        {"factory": {"cross_check": {"performed": True, "agreed": False,
            "diagnosis": {"kind": "verdict_mismatch", "likely_codegen_variance": True}}}},
        {"factory": {"cross_check": {"performed": True, "agreed": True,
            "diagnosis": {"kind": "agree", "likely_codegen_variance": False}}}},
        {"cross_check": {"performed": True, "agreed": False,
            "diagnosis": {"kind": "metric_divergence", "likely_codegen_variance": False}}},
    ]
    s = crosscheck_summary(exps)
    assert s["cross_checks"] == 3
    assert s["likely_codegen_variance"] == 1
    assert s["by_kind"]["verdict_mismatch"] == 1
