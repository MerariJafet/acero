"""External review bundle generation + version binding + blind export (Sprint 19).

Builds a self-contained, LOCAL bundle a human could hand to an external reviewer. Every bundle
is BOUND to a version fingerprint (commit + artifact hashes); a structured review only applies
to the version it was written against. A blinded variant removes reviewer-facing identity but
NEVER removes information needed for reproducibility.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.hashing import hash_json, hash_text
from .licensing import check_licenses
from .questions import REVIEW_QUESTIONS

AI_USE_TEXT = (
    "AI assistance disclosure: ACERO (an AI system) assisted with computation, analysis and "
    "drafting. ACERO is NOT an author and claims NO discovery. All results are computational "
    "and require independent human scientific review and, where applicable, external "
    "experimental validation. Preparing a review bundle is NOT external review."
)


class BlindMode(str, Enum):
    OPEN_IDENTITY = "OPEN_IDENTITY"
    PARTIALLY_BLINDED = "PARTIALLY_BLINDED"
    BLINDED = "BLINDED"


class BundleError(RuntimeError):
    """Raised when a bundle cannot be built (e.g. license blocked)."""


def version_fingerprint(*, commit: str, artifact_hashes: dict[str, str]) -> dict[str, Any]:
    return {"commit": commit, "artifact_hashes": artifact_hashes,
            "fingerprint": hash_json({"commit": commit, "artifacts": artifact_hashes})}


def build_bundle(out_dir: str | Path, *, project: str, central_claims: list[dict[str, Any]],
                 methods: str, evidence_map: list[dict[str, Any]],
                 counterevidence: list[dict[str, Any]], limitations: list[str],
                 reliability_card: dict[str, Any], commit: str,
                 licenses: dict[str, str], blind: BlindMode = BlindMode.OPEN_IDENTITY,
                 author: str = "human researcher") -> dict[str, Any]:
    """Write the external_review_bundle/ locally. Blocks if any license is incompatible/unknown."""
    lic = check_licenses(licenses)
    if not lic["ok"]:
        raise BundleError(f"license check failed: blocked={lic['blocked']} unknown={lic['unknown']}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reproduction").mkdir(exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)

    author_shown = author if blind == BlindMode.OPEN_IDENTITY else "[blinded]"
    files: dict[str, str] = {}

    def _write(name: str, content: str) -> None:
        (out / name).write_text(content, encoding="utf-8")
        files[name] = hash_text(content)

    _write("README.md", f"# External Review Bundle — {project}\n\n{AI_USE_TEXT}\n\n"
                        "Local materials for independent human review. NOT a publication.\n")
    _write("executive_summary.md", f"# Executive summary\n\nAuthor: {author_shown}\n\n"
           f"{len(central_claims)} central claim(s); {len(evidence_map)} evidence item(s); "
           f"{len(counterevidence)} counter-evidence item(s).\n")
    _write("scientific_question.md", f"# Scientific question\n\n{project}\n")
    _write("central_claims.json", json.dumps(central_claims, indent=2))
    _write("methods.md", f"# Methods\n\n{methods}\n")
    _write("evidence_map.json", json.dumps(evidence_map, indent=2))
    _write("counterevidence.json", json.dumps(counterevidence, indent=2))
    _write("limitations.md", "# Limitations\n\n" + "\n".join(f"- {x}" for x in limitations))
    _write("reliability_card.json", json.dumps(reliability_card, indent=2))
    _write("review_questions.md", "# Review questions\n\n" +
           "\n".join(f"- {q}" for q in REVIEW_QUESTIONS))
    _write("reviewer_form.json", json.dumps({
        "reviewer_role": "one of DOMAIN_EXPERT/STATISTICIAN/METHODS_REVIEWER/...",
        "reviewed_version": commit, "overall_assessment": "", "major_concerns": [],
        "minor_concerns": [], "claim_comments": [], "method_comments": [],
        "reproduction_result": "reproduced|failed|not_attempted", "requested_changes": [],
        "confidence": 0.5}, indent=2))
    _write("AI_USE.md", f"# AI use\n\n{AI_USE_TEXT}\n")
    _write("LICENSE", "\n".join(f"{k}: {v}" for k, v in licenses.items()) + "\n")

    fp = version_fingerprint(commit=commit, artifact_hashes=dict(files))
    _write("version_binding.json", json.dumps(fp, indent=2))

    # checksums over everything except itself
    checks = "\n".join(f"{h}  {n}" for n, h in files.items()) + "\n"
    (out / "checksums.txt").write_text(checks, encoding="utf-8")

    return {"dir": str(out), "blind": blind.value, "n_files": len(files),
            "version_fingerprint": fp["fingerprint"], "commit": commit,
            "license_ok": True, "auto_published": False, "exported_at": now_iso()}
