"""Symmetries, invariants and conservation (Sprint 8.7).

A documented Noether-INSPIRED lookup from continuous symmetries to conserved
quantities. This is NOT a proof of Noether's theorem — it is a verifiable
association used to constrain candidate models, flagged as such.
"""

from __future__ import annotations

from typing import Any

# symmetry -> (conserved quantity candidate, note)
SYMMETRY_TO_CONSERVATION: dict[str, tuple[str, str]] = {
    "time_translation": ("energy", "Noether-inspired association (not a proof here)"),
    "space_translation": ("linear_momentum", "Noether-inspired association"),
    "rotation": ("angular_momentum", "Noether-inspired association"),
    "gauge": ("charge", "Noether-inspired association; gauge treated as concept only"),
    "scale": ("none", "scale invariance does not yield a simple conserved quantity"),
    "permutation": ("none", "identical-particle symmetry; statistics, not a scalar charge"),
    "inversion": ("parity", "discrete symmetry; parity is not continuously conserved"),
}

CONSERVATION_QUANTITIES = {"mass", "energy", "linear_momentum", "angular_momentum",
                           "charge", "probability", "population"}


def conservation_candidate(symmetry: str) -> dict[str, Any]:
    if symmetry not in SYMMETRY_TO_CONSERVATION:
        return {"symmetry": symmetry, "conserved": None,
                "note": "unknown symmetry; no association"}
    q, note = SYMMETRY_TO_CONSERVATION[symmetry]
    return {"symmetry": symmetry, "conserved": None if q == "none" else q, "note": note}


def check_conservation(model_conserves: list[str], required: list[str]) -> dict[str, Any]:
    """Does a candidate model conserve everything the problem requires?"""
    missing = [q for q in required if q not in model_conserves]
    return {"ok": not missing, "missing": missing,
            "unknown_quantities": [q for q in model_conserves if q not in CONSERVATION_QUANTITIES]}
