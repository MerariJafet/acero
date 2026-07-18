"""Materialize the transit research dossier tree (Sprint 24 §24.15).

Writes a complete, self-describing dossier directory from a program result. This
is evidence for human review — it makes NO discovery claim and clearly separates
real data, injected signals, controls, and nulls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...core.config import repo_root
from . import data
from . import preregistration as prereg

_SUBDIRS = [
    "preregistration", "data_manifests", "literature", "code", "experiments",
    "null_tests", "signal_injection", "figures", "tables", "negative_results",
    "reliability", "learning", "review", "publication_candidate", "website_note",
]


def dossier_root() -> Path:
    return repo_root() / "research" / "artifacts" / "transit" / "research_dossier"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def build_dossier(result: dict[str, Any]) -> Path:
    root = dossier_root()
    for d in _SUBDIRS:
        (root / d).mkdir(parents=True, exist_ok=True)

    _write(root / "README.md",
           "# Transit Signal Robustness Dossier (Kepler-8b)\n\n"
           "**This dossier makes NO discovery claim.** It documents how robustly a "
           "KNOWN transit is recovered, and where the pipeline must abstain.\n\n"
           f"- Preregistration hash: `{result['preregistration_hash']}`\n"
           f"- Target: {data.TARGET_NAME}; Control: {data.CONTROL_NAME}\n"
           f"- Verdict (bounded claim): **{result['abstention_supported_claim']['verdict']}**\n"
           f"- Forced hard-case verdict: **{result['abstention_forced_hard_case']['verdict']}**\n")

    _write(root / "preregistration" / "preregistration.json",
           json.dumps({"preregistration": prereg.PREREGISTRATION,
                       "sha256": result["preregistration_hash"]}, indent=2))
    _write(root / "data_manifests" / "data_manifests.json",
           json.dumps(data.acquire_program(downloaded_at="dossier"), indent=2))
    _write(root / "literature" / "references.md",
           f"- {data.REFERENCE}\n- MAST archive: {data.MAST_BASE}\n")
    _write(root / "code" / "POINTER.md",
           "Analysis code: `src/acero/studies/transit/` "
           "(data, pipelines, injection, nulls, abstention, program).\n")
    _write(root / "experiments" / "pipelines.json",
           json.dumps({"pipeline_A": result["pipeline_A"], "pipeline_B": result["pipeline_B"],
                       "agreement": result["period_agreement"],
                       "stability": result["period_stability"],
                       "period_recovery_frac_error": result["period_recovery_frac_error"]}, indent=2))
    _write(root / "null_tests" / "nulls.json", json.dumps(result["null_tests"], indent=2))
    _write(root / "signal_injection" / "injection.json",
           json.dumps({"recovery": result["injection_recovery"],
                       "calibration": result["calibration"]}, indent=2))
    _write(root / "negative_results" / "negative_results.md",
           "# Preserved negative results\n\n"
           f"- Null tests NOT fully controlled (FPR={result['null_tests']['false_positive_rate']}): "
           "AR(1) red noise and inverted-transit nulls produced detections.\n"
           f"- False-positive scenarios triggering detections: "
           f"{result['false_positive_scenarios']['n_false_detections']} of "
           f"{result['false_positive_scenarios']['n']}.\n"
           "- Consequence: the Abstention Engine abstained from the bounded claim. "
           "This negative result is preserved, not discarded.\n")
    _write(root / "reliability" / "abstention.json",
           json.dumps({"supported_claim": result["abstention_supported_claim"],
                       "forced_hard_case": result["abstention_forced_hard_case"],
                       "false_positive_scenarios": result["false_positive_scenarios"]}, indent=2))
    _write(root / "learning" / "curriculum.md",
           "Human Understanding curriculum: `transit` "
           "(recovery_is_not_discovery, injection_is_not_observation, "
           "same_data_not_independent, when_to_abstain are BLOCKING concepts).\n")
    _write(root / "review" / "review_questions.md",
           "1. Why is recovering Kepler-8b not a discovery?\n"
           "2. Why is an injected signal not an observation?\n"
           "3. Why are two pipelines over the same data not independent replication?\n"
           "4. Given the uncontrolled red-noise nulls, is even the bounded claim justified?\n")
    _write(root / "publication_candidate" / "status.md",
           "Status: NOT a publication candidate. Auto-publication forbidden. "
           "External human review required. No discovery.\n")
    _write(root / "website_note" / "note.md",
           "Local note only. Nothing is published or sent externally.\n")
    _write(root / "tables" / "summary.md",
           f"| metric | value |\n|---|---|\n"
           f"| recovered period (A) | {result['pipeline_A']['period']} d |\n"
           f"| known period | {result['known_period']} d |\n"
           f"| period frac error | {result['period_recovery_frac_error']} |\n"
           f"| injection recovery | {result['injection_recovery']['recovery_rate']} |\n"
           f"| null FPR | {result['null_tests']['false_positive_rate']} |\n"
           f"| verdict | {result['abstention_supported_claim']['verdict']} |\n")
    return root
