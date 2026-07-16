"""Licensing review (Sprint 19).

Checks code/data/figures/text/dataset/dependency licenses; BLOCKS a bundle with an
incompatible or unknown license. Conservative: unknown = blocked (a human resolves it).
"""

from __future__ import annotations

from typing import Any

# Licenses considered shareable-for-review here (permissive / public domain).
_ALLOWED = {"MIT", "BSD-3-Clause", "Apache-2.0", "CC0", "CC-BY-4.0", "public-domain",
            "public domain"}
_INCOMPATIBLE = {"proprietary", "no-redistribution", "confidential", "all-rights-reserved"}


def check_licenses(components: dict[str, str]) -> dict[str, Any]:
    """components: {name: license_string}. Returns ok + reasons."""
    blocked: list[str] = []
    unknown: list[str] = []
    for name, lic in components.items():
        lic_norm = (lic or "").strip()
        if lic_norm in _INCOMPATIBLE:
            blocked.append(f"{name}: incompatible ({lic_norm})")
        elif lic_norm not in _ALLOWED:
            unknown.append(f"{name}: unknown/unspecified ({lic_norm or 'none'})")
    ok = not blocked and not unknown
    return {"ok": ok, "blocked": blocked, "unknown": unknown,
            "note": "unknown or incompatible licenses BLOCK the bundle; a human must resolve"}
