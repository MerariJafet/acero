"""Regression detection (Sprint 18).

Compares a fresh benchmark result against a LOCKED baseline using PRE-REGISTERED tolerances
(never adjusted after seeing results). A small variation within tolerance is UNCHANGED, not a
regression. Metrics are higher-is-better unless listed in _LOWER_IS_BETTER.
"""

from __future__ import annotations

from typing import Any

from .models import RegressionStatus

# Pre-registered per-metric tolerances (absolute). Fixed; do not tune to results.
_TOLERANCE: dict[str, float] = {
    "pass_rate": 0.0,          # gauntlets must stay perfect
    "detection_rate": 0.0,
    "caught_rate": 0.0,
    "recovery_rate": 0.05,
    "period_years": 0.5,       # astronomy period may vary within 0.5 yr
    "duration_sec": 2.0,       # latency tolerance before flagging
}
_LOWER_IS_BETTER = {"duration_sec", "ece", "abstention_rate", "false_positive_rate"}
_DEFAULT_TOL = 0.02


def _direction(metric: str) -> int:
    return -1 if metric in _LOWER_IS_BETTER else 1


def compare_metric(metric: str, baseline: float, current: float) -> RegressionStatus:
    tol = _TOLERANCE.get(metric, _DEFAULT_TOL)
    delta = (current - baseline) * _direction(metric)
    if abs(current - baseline) <= tol:
        return RegressionStatus.UNCHANGED
    return RegressionStatus.IMPROVED if delta > 0 else RegressionStatus.REGRESSED


def compare_benchmark(baseline: dict[str, Any] | None, current: dict[str, Any]
                      ) -> dict[str, Any]:
    """Compare one benchmark's current run against its baseline entry."""
    if baseline is None:
        return {"status": RegressionStatus.INSUFFICIENT_DATA.value, "per_metric": {}}
    per_metric: dict[str, str] = {}
    worst = RegressionStatus.UNCHANGED
    order = [RegressionStatus.IMPROVED, RegressionStatus.UNCHANGED,
             RegressionStatus.REGRESSED]
    for metric, cur in current.get("metrics", {}).items():
        base = baseline.get("metrics", {}).get(metric)
        if base is None:
            per_metric[metric] = RegressionStatus.INSUFFICIENT_DATA.value
            continue
        st = compare_metric(metric, float(base), float(cur))
        per_metric[metric] = st.value
        if order.index(st) > order.index(worst) if st in order else False:
            worst = st
    # latency check
    if "duration_sec" in current and baseline.get("duration_sec") is not None:
        lat = compare_metric("duration_sec", float(baseline["duration_sec"]),
                             float(current["duration_sec"]))
        per_metric["duration_sec"] = lat.value
        if lat == RegressionStatus.REGRESSED:
            worst = RegressionStatus.REGRESSED
    return {"status": worst.value, "per_metric": per_metric}


def compare_run(baseline_results: dict[str, Any], current_results: dict[str, Any]
                ) -> dict[str, Any]:
    """Compare a full run vs the baseline; return per-benchmark statuses + any regressions."""
    out: dict[str, Any] = {}
    regressions = []
    for bid, cur in current_results.get("results", {}).items():
        base = baseline_results.get("results", {}).get(bid)
        cmp = compare_benchmark(base, cur)
        out[bid] = cmp
        if cmp["status"] == RegressionStatus.REGRESSED.value:
            regressions.append(bid)
    return {"per_benchmark": out, "regressions": regressions,
            "has_regression": bool(regressions)}
