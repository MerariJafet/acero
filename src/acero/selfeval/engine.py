"""Scientific Capability Evaluation Engine (Sprint 18) — orchestrator.

Runs the benchmark suite, compares against the locked baseline (regression detection), and
assembles a capability status view. It NEVER self-approves: it reports evidence and defers
every consequential decision to a human. More tests/code are not treated as improvement.
"""

from __future__ import annotations

from typing import Any

from . import baseline, benchmarks, prompts
from .capabilities import default_capabilities
from .codex_drift import detect_drift
from .models import CapabilityStatus
from .regression import compare_run


def run_evaluation(*, baseline_version: str = "v2.0.0-rc1") -> dict[str, Any]:
    """Run all benchmarks; compare vs baseline if present; refresh capability statuses."""
    current = benchmarks.run_all()
    has_baseline = baseline.exists(baseline_version)
    if has_baseline:
        base = baseline.load(baseline_version)
        regression = compare_run(base, current)
    else:
        # No baseline ⇒ we cannot claim NO_REGRESSION (nothing was compared). Report it
        # honestly as insufficient rather than overreaching (Codex-audit fix).
        regression = {"per_benchmark": {}, "regressions": [],
                      "has_regression": False, "no_baseline": True}

    # capability status is driven by EVIDENCE. A failing benchmark DEGRADES a capability; a
    # passing benchmark keeps its DECLARED status but never auto-PROMOTES it (promoting on a
    # single passing run would be exactly the self-deception this engine must avoid — e.g.
    # astronomy stays EXPERIMENTAL on one dataset). Promotion is a human decision.
    caps = []
    for cap in default_capabilities():
        bench_ids = [b for b in cap.benchmark_suite if b in current["results"]]
        results = [current["results"][b]["passed"] for b in bench_ids]
        if results and not all(results):
            status = CapabilityStatus.DEGRADED
        else:
            status = cap.status                     # declared status preserved (no auto-promote)
        caps.append({"name": cap.name, "domain": cap.domain, "status": status.value,
                     "benchmarks": bench_ids, "limitations": cap.limitations})

    return {
        "version": current["version"], "commit": current["commit"],
        "benchmarks": {b: {"passed": r["passed"], "metrics": r["metrics"],
                           "duration_sec": r["duration_sec"]}
                       for b, r in current["results"].items()},
        "regression": regression,
        "capabilities": caps,
        "prompts": prompts.run(),
        "codex_drift": detect_drift(None),
        "verdict": ("REGRESSION_DETECTED" if regression.get("has_regression")
                    else "NO_REGRESSION" if has_baseline
                    else "INSUFFICIENT_BASELINE"),
        "note": "self-evaluation reports evidence against ACERO's OWN (not independent) "
                "benchmarks; NO_REGRESSION means only 'no change vs the locked baseline'. It "
                "never self-approves and never treats more tests/code as improvement. A human "
                "decides.",
    }


def lock_baseline(version: str, *, force: bool = False) -> dict[str, Any]:
    """Run all benchmarks and lock them as the baseline for ``version``."""
    current = benchmarks.run_all()
    return baseline.write(version, current, force=force)
