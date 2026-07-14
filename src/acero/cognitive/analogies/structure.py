"""Structural comparison of two systems — the heart of deep-analogy detection.

We do NOT rely on embeddings. We compare the canonical form of the governing
equation, the mapping of domain-neutral term roles, the correspondence of named
dimensionless groups, invariants and symmetries, and (weighted low) surface name
similarity.
"""

from __future__ import annotations

import re
from typing import Any

from .models import AnalogyScores, SystemRepresentation

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_TOKEN.findall(s.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a or b) else 0.0


def _form_category(form: str) -> str:
    return form.split(":", 1)[0].strip().lower() if form else ""


def compare(source: SystemRepresentation, target: SystemRepresentation) -> dict[str, Any]:
    """Return a structural comparison of two systems (used to build scores + mapping)."""
    forms_match = (_form_category(source.structural_form) == _form_category(target.structural_form)
                   and bool(source.structural_form))

    shared_roles = set(source.term_roles) & set(target.term_roles)
    union_roles = set(source.term_roles) | set(target.term_roles)
    role_mapping = {source.term_roles[r]: target.term_roles[r] for r in shared_roles}
    role_completeness = len(shared_roles) / len(union_roles) if union_roles else 0.0

    shared_groups = set(source.dimensionless_groups) & set(target.dimensionless_groups)
    union_groups = set(source.dimensionless_groups) | set(target.dimensionless_groups)
    group_overlap = len(shared_groups) / len(union_groups) if union_groups else 0.0

    shared_inv = set(source.invariants) & set(target.invariants)
    shared_sym = set(source.symmetries) & set(target.symmetries)

    surface = _jaccard(_tokens(source.name + " " + " ".join(source.variables)),
                       _tokens(target.name + " " + " ".join(target.variables)))

    return {
        "forms_match": forms_match,
        "form_category": _form_category(source.structural_form),
        "role_mapping": role_mapping,
        "role_completeness": round(role_completeness, 4),
        "shared_roles": sorted(shared_roles),
        "missing_roles": sorted(union_roles - shared_roles),
        "shared_dimensionless_groups": sorted(shared_groups),
        "group_overlap": round(group_overlap, 4),
        "shared_invariants": sorted(shared_inv),
        "shared_symmetries": sorted(shared_sym),
        "surface_similarity": round(surface, 4),
    }


def score(comparison: dict[str, Any]) -> AnalogyScores:
    """Turn a structural comparison into separate, transparent scores."""
    forms = 1.0 if comparison["forms_match"] else 0.0
    role_c = comparison["role_completeness"]
    groups = comparison["group_overlap"]
    surface = comparison["surface_similarity"]

    structural = forms * role_c
    mathematical = role_c if comparison["forms_match"] else 0.15 * role_c
    invariant = groups
    predictive = groups if comparison["forms_match"] else 0.0
    boundary = 0.5 * (role_c + groups) / 1.0
    # Misleading risk: high surface similarity but low deep structure.
    failure_risk = max(0.0, surface - 0.5 * (structural + groups))
    return AnalogyScores(
        structural_similarity=round(structural, 4),
        mathematical_similarity=round(mathematical, 4),
        causal_similarity=round(structural, 4),         # proxy: causal follows structure here
        invariant_preservation=round(invariant, 4),
        boundary_compatibility=round(min(1.0, boundary), 4),
        predictive_transferability=round(predictive, 4),
        surface_similarity=round(surface, 4),
        failure_risk=round(min(1.0, failure_risk), 4))
