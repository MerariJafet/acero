"""Derivation verification (Sprint 8.7).

Codex may PROPOSE derivation steps, but SymPy verifies them. A symbolic step asserts
an identity that must simplify to zero; a dimensional step must be dimensionally
consistent. Unverified steps are tracked as 'unresolved' — never hidden.
"""

from __future__ import annotations

from ..dimensions import Dimension, equation_consistent
from .models import DerivationStep, ScientificDerivation


def verify_symbolic_step(step: DerivationStep) -> DerivationStep:
    """A symbolic step's ``expression`` is an identity expected to simplify to 0."""
    import sympy as sp

    try:
        expr = sp.simplify(sp.sympify(step.expression))
        ok = expr == 0
        step.verified = bool(ok)
        step.detail = "simplifies to 0" if ok else f"does not vanish: {expr}"
    except Exception as exc:  # noqa: BLE001 - a bad step is unverified, not a crash
        step.verified = False
        step.detail = f"symbolic check failed: {exc}"
    return step


def verify_dimensional_step(step: DerivationStep, lhs: Dimension, rhs: Dimension) -> DerivationStep:
    ok = equation_consistent(lhs, rhs)
    step.verified = ok
    step.detail = f"dimensions {'match' if ok else 'MISMATCH'}: {lhs} vs {rhs}"
    return step


def verify_derivation(derivation: ScientificDerivation) -> ScientificDerivation:
    """Verify all symbolic steps; leave dimensional/numerical as provided. Confidence
    is the fraction of checkable steps that pass (never 1.0 — derivations are
    provisional)."""
    for step in derivation.steps:
        if step.check_kind == "symbolic" and not step.verified:
            verify_symbolic_step(step)
    checkable = [s for s in derivation.steps if s.check_kind != "none"]
    if checkable:
        frac = sum(1 for s in checkable if s.verified) / len(checkable)
        derivation.confidence = round(min(0.9, frac), 4)  # capped; Codex never certifies
    else:
        derivation.confidence = 0.0
    return derivation
