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
                       "multi_domain", "gate_bypass", "stellar_variability",
                       "exoplanet_transit_robustness", "self_evaluation",
                       "external_review_gauntlet"],
        "datasets": [{"name": "SILSO sunspots", "license": "public domain", "gated": True},
                     {"name": "NASA exoplanets", "license": "public", "gated": True},
                     {"name": "Kepler-8 + control light curves", "license": "public domain",
                      "gated": True}],
        "licenses": {"code": "Apache-2.0", "datasets": "public/public-domain only"},
        "security": {"auto_publication": False, "sandbox": "subprocess/docker",
                     "secrets": "env HMAC (never in Git)", "inline_gate": True,
                     "portal_auth": "PBKDF2 + server sessions + CSRF + rate limit"},
        "compatibility": {"python": "3.12", "db": "SQLite (PostgreSQL optional)"},
        "known_issues": [
            "portal is a modular vanilla-JS SPA (per ADR-PORTAL-STACK-V2); real Playwright "
            "browser E2E + pytest route/DOM/security tests",
            "runtime uses real multiprocess workers over on-disk SQLite; no long-lived daemon",
            "two astronomy studies (sunspots, transit); instrument/pipeline dependence "
            "still not exhaustively assessed",
            "transit program ABSTAINS: naive BLS-SNR does not control red-noise false "
            "positives (preserved negative result, not a defect to hide)",
            "self-evaluation uses ACERO's own benchmarks — NOT independent evaluation",
            "reproduction is INDEPENDENT_PROCESS_REPRODUCTION — NOT external replication; "
            "external review preparation is NOT external review; nothing is sent or contacted",
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

    # Sprint 18/19 additions
    from ..selfeval.engine import run_evaluation
    ev = run_evaluation()
    _record("self_evaluation", not ev["regression"].get("has_regression"),
            ev["verdict"])
    from sqlalchemy import create_engine

    from ..benchmarks.external_review_gauntlet import run_external_review_gauntlet
    from ..discovery.store import DiscoveryStore
    from ..ledger.db import make_session_factory
    from ..ledger.models import Base
    from ..ledger.service import ResearchLedger
    eng = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(eng)
    sf = make_session_factory(eng)
    store = DiscoveryStore(sf, ResearchLedger(sf))
    with tempfile.TemporaryDirectory() as td:
        erg = run_external_review_gauntlet(td, store)
    _record("external_review", erg["all_passed"], f"{erg['passed']}/{erg['n']}")

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
