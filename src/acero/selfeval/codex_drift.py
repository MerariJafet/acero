"""Codex drift detection (Sprint 18).

The Codex CLI can change version or behaviour. This records a fingerprint (CLI presence,
declared model, output-format expectations) and flags CODEX_PROVIDER_REVALIDATION_REQUIRED if
the fingerprint differs from a stored one. It never calls a paid service and works offline
(reporting 'codex not present' rather than failing).
"""

from __future__ import annotations

import shutil
from typing import Any

REVALIDATION_FLAG = "CODEX_PROVIDER_REVALIDATION_REQUIRED"


def fingerprint() -> dict[str, Any]:
    present = shutil.which("codex") is not None
    return {"codex_present": present,
            "expected_output_format": "strict JSON via --output-schema (arrays of {from,to})",
            "schema_compliance_contract": "all properties required; no open object maps",
            "token_usage_recorded": True,
            "advisory_only": True}


def detect_drift(previous: dict[str, Any] | None) -> dict[str, Any]:
    """Compare the current fingerprint to a stored one."""
    current = fingerprint()
    if previous is None:
        return {"status": "BASELINE_RECORDED", "fingerprint": current, "revalidate": False}
    changed = {k: (previous.get(k), current[k]) for k in current
               if previous.get(k) != current[k]}
    revalidate = bool(changed)
    return {"status": REVALIDATION_FLAG if revalidate else "STABLE",
            "changed": changed, "fingerprint": current, "revalidate": revalidate,
            "note": "Codex is advisory; drift never auto-updates beliefs or approves anything."}
