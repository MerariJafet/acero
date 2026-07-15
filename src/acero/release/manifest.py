"""Release manifest + final acceptance (Sprint 20).

Assembles the RC manifest (version, modules, tests, benchmarks, datasets, limitations,
known issues) and runs a FINAL ACCEPTANCE that executes every gauntlet. Acceptance never
'passes' a release by itself — it reports; a human decides.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ..core.config import repo_root


def build_manifest() -> dict[str, Any]:
    from .. import __version__
    from ..core.schema_version import CURRENT_SCHEMA_VERSION
    from ..epistemic_gate.registry import GateRegistry
    root = repo_root()
    src = root / "src" / "acero"
    packages = sorted(p.name for p in src.iterdir()
                      if p.is_dir() and (p / "__init__.py").exists()
                      and p.name != "__pycache__")
    commit = _git("rev-parse", "--short", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    return {
        "name": "ACERO",
        "version": __version__,
        "commit": commit,
        "branch": branch,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "packages": packages,
        "n_packages": len(packages),
        "gate_rules": len(GateRegistry().all_rules()),
        "benchmarks": ["governing_dynamics", "cross_domain", "human_understanding",
                       "reliability_gauntlet", "review_gauntlet", "chaos_gauntlet",
                       "multi_domain", "gate_bypass"],
        "datasets": [{"name": "SILSO sunspots", "license": "public domain", "gated": True},
                     {"name": "NASA exoplanets", "license": "public", "gated": True}],
        "licenses": {"code": "see repository", "datasets": "public/public-domain only"},
        "security": {"auto_publication": False, "sandbox": "subprocess/docker",
                     "secrets": "env HMAC (never in Git)", "inline_gate": True},
        "compatibility": {"python": "3.12", "db": "SQLite (PostgreSQL optional)"},
        "known_issues": [
            "portal is a vanilla-JS SPA (no Vitest/Playwright) — pytest route/DOM/security tests",
            "worker drains synchronously (no long-lived daemon)",
            "single astronomy study; instrument/pipeline dependence not assessed",
            "no Alembic (idempotent create_all + lightweight schema versioning)",
        ],
    }


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(repo_root()),
                              capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def final_acceptance() -> dict[str, Any]:
    """Run every gauntlet and report. Does NOT declare the release approved."""
    from ..benchmarks.chaos_gauntlet import run_chaos_gauntlet
    from ..benchmarks.reliability_gauntlet import run_gauntlet as reliability
    from ..reliability.mutation import run_mutation_testing
    from ..reliability.red_team import run_red_team

    gauntlets: dict[str, dict[str, Any]] = {}

    def _record(name: str, all_passed: bool, detail: str) -> None:
        gauntlets[name] = {"all_passed": all_passed, "detail": detail}

    r = reliability()
    _record("reliability", r["all_passed"], f"{r['passed']}/{r['n']}")
    c = run_chaos_gauntlet()
    _record("chaos", c["all_passed"], f"{c['passed']}/{c['n']}")
    rt = run_red_team().as_dict()
    _record("red_team", not rt["missed"], f"{rt['detected']}/{rt['n']}")
    mt = run_mutation_testing().as_dict()
    _record("mutation", not mt["survived"], f"{mt['caught']}/{mt['n']}")
    import tempfile

    from ..benchmarks.review_gauntlet import run_review_gauntlet
    with tempfile.TemporaryDirectory() as td:
        rv = run_review_gauntlet(td)
    _record("review", rv["all_passed"], f"{rv['passed']}/{rv['n']}")

    all_passed = all(g["all_passed"] for g in gauntlets.values())
    return {"gauntlets": gauntlets, "all_gauntlets_passed": all_passed,
            "verdict": "RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW" if all_passed
                       else "BLOCKERS_PRESENT",
            "note": "acceptance reports; it never approves a release — a human decides. "
                    "No auto-publication; no discovery claimed."}


def write_manifest(path: str | Path | None = None) -> str:
    import json
    p = Path(path) if path else repo_root() / "docs" / "releases" / "release_manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(build_manifest(), indent=2), encoding="utf-8")
    return str(p)
