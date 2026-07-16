"""Benchmark registry + runner (Sprint 18).

Centralises the existing benchmarks behind one interface, records commit/env/duration, and
compares against a locked baseline. Acceptance thresholds are FIXED here (pre-registered) and
must not be edited after seeing results.
"""

from __future__ import annotations

import platform
import subprocess
import time
from collections.abc import Callable
from typing import Any

from .. import __version__
from ..core.clock import now_iso
from ..core.config import repo_root
from .models import BenchmarkDefinition

# metric extractor: run the benchmark, return {metric: value}
_Extractor = Callable[[], dict[str, float]]


def _reliability() -> dict[str, float]:
    from ..benchmarks.reliability_gauntlet import run_gauntlet
    r = run_gauntlet()
    return {"pass_rate": r["passed"] / r["n"]}


def _chaos() -> dict[str, float]:
    from ..benchmarks.chaos_gauntlet import run_chaos_gauntlet
    r = run_chaos_gauntlet()
    return {"pass_rate": r["passed"] / r["n"]}


def _red_team() -> dict[str, float]:
    from ..reliability.red_team import run_red_team
    r = run_red_team().as_dict()
    return {"detection_rate": r["detected"] / r["n"]}


def _mutation() -> dict[str, float]:
    from ..reliability.mutation import run_mutation_testing
    r = run_mutation_testing().as_dict()
    return {"caught_rate": r["caught"] / r["n"]}


def _review() -> dict[str, float]:
    import tempfile

    from ..benchmarks.review_gauntlet import run_review_gauntlet
    with tempfile.TemporaryDirectory() as td:
        r = run_review_gauntlet(td)
    return {"pass_rate": r["passed"] / r["n"]}


def _governing() -> dict[str, float]:
    from ..benchmarks.governing_dynamics import run_governing_dynamics
    r = run_governing_dynamics()
    recovered = sum(1 for v in r["level1_recovery"].values() if v["recovered"])
    return {"recovery_rate": recovered / max(1, len(r["level1_recovery"]))}


def _stellar() -> dict[str, float]:
    from ..core.config import repo_root as _rr
    csv = _rr() / "research" / "datasets" / "sunspots.csv"
    if not csv.exists():
        return {"period_years": 0.0}       # dataset offline; runner records INSUFFICIENT
    from ..studies.stellar_variability import run_program
    return {"period_years": run_program(n_surrogates=60)["analysis"]["dominant_period_years"]}


_REGISTRY: dict[str, tuple[BenchmarkDefinition, _Extractor]] = {
    "reliability_gauntlet": (BenchmarkDefinition(
        id="reliability_gauntlet", purpose="detect what should be detected / abstain",
        metrics=["pass_rate"], acceptance_thresholds={"pass_rate": 1.0},
        leakage_risks=["deterministic detectors; no data leakage"]), _reliability),
    "chaos_runtime": (BenchmarkDefinition(
        id="chaos_runtime", purpose="runtime survives faults",
        metrics=["pass_rate"], acceptance_thresholds={"pass_rate": 1.0}), _chaos),
    "red_team": (BenchmarkDefinition(
        id="red_team", purpose="catch scientific attacks", metrics=["detection_rate"],
        acceptance_thresholds={"detection_rate": 1.0}), _red_team),
    "mutation": (BenchmarkDefinition(
        id="mutation", purpose="gate catches scientific mutations", metrics=["caught_rate"],
        acceptance_thresholds={"caught_rate": 1.0}), _mutation),
    "publication_review": (BenchmarkDefinition(
        id="publication_review", purpose="review→gated-export blocks correctly",
        metrics=["pass_rate"], acceptance_thresholds={"pass_rate": 1.0}), _review),
    "governing_dynamics": (BenchmarkDefinition(
        id="governing_dynamics", purpose="recover hidden ODEs", metrics=["recovery_rate"],
        acceptance_thresholds={"recovery_rate": 0.8},
        known_biases=["synthetic data; imposed library"]), _governing),
    "stellar_variability": (BenchmarkDefinition(
        id="stellar_variability", purpose="real SILSO period (no discovery)",
        metrics=["period_years"], acceptance_thresholds={"period_years": 10.0},
        known_biases=["single dataset"], leakage_risks=["none — descriptive"]), _stellar),
}


def definitions() -> list[BenchmarkDefinition]:
    return [d for d, _ in _REGISTRY.values()]


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(repo_root()),
                              capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def run_one(bench_id: str) -> dict[str, Any]:
    if bench_id not in _REGISTRY:
        raise KeyError(f"unknown benchmark {bench_id!r}; have {sorted(_REGISTRY)}")
    definition, extractor = _REGISTRY[bench_id]
    t0 = time.monotonic()
    metrics = extractor()
    duration = round(time.monotonic() - t0, 3)
    passed = all(metrics.get(m, 0.0) >= th
                 for m, th in definition.acceptance_thresholds.items())
    return {"benchmark": bench_id, "metrics": metrics, "passed": passed,
            "duration_sec": duration, "commit": _git_commit(), "version": __version__,
            "environment": {"python": platform.python_version(), "platform": platform.system()},
            "thresholds": definition.acceptance_thresholds, "at": now_iso()}


def run_all() -> dict[str, Any]:
    results = {bid: run_one(bid) for bid in _REGISTRY}
    return {"results": results, "n": len(results),
            "passed": sum(1 for r in results.values() if r["passed"]),
            "commit": _git_commit(), "version": __version__, "at": now_iso()}
