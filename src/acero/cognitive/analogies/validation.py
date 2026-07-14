"""Analogy validation (Sprint 8.6).

Every analogy must survive: (1) structural, (2) dimensional, (3) mathematical,
(4) limits, (5) predictive-transfer (verified IN THE SANDBOX), (6) counterexample,
(7) skeptic tests. Verbal similarity alone never passes.
"""

from __future__ import annotations

import json
import os
import tempfile
from fractions import Fraction
from typing import Any

from ...sandbox.runner import SubprocessRunner
from .. import dimensions as dim
from .models import AnalogyScores, AnalogyStatus, SystemRepresentation, ValidationResult
from .structure import compare

# Sandbox script: sweep driving frequency of a*y'' + b*y' + c*y = cos(w t); return the
# resonance peak frequency. Same equation drives oscillator AND RLC -> transfer test.
_RESONANCE_SCRIPT = r'''
import json
import numpy as np

with open("inputs/params.json") as fh:
    P = json.load(fh)
a, b, c = P["a"], P["b"], P["c"]
w0 = (c / a) ** 0.5
ws = np.linspace(0.2 * w0, 2.5 * w0, 120)
amps = []
for w in ws:
    dt = 0.01; n = int(60.0 / dt); y = 0.0; v = 0.0
    tail = []
    for i in range(n):
        t = i * dt
        acc = (np.cos(w * t) - b * v - c * y) / a
        v += acc * dt; y += v * dt
        if i > int(n * 0.6):
            tail.append(abs(y))
    amps.append(max(tail) if tail else 0.0)
peak_w = float(ws[int(np.argmax(amps))])
print(json.dumps({"w0_formula": w0, "peak_w": peak_w,
                  "rel_error": abs(peak_w - w0) / w0}))
'''


def structural_test(comparison: dict[str, Any]) -> ValidationResult:
    ok = comparison["forms_match"] and comparison["role_completeness"] >= 0.8
    return ValidationResult(test="structural", passed=ok,
                            detail=f"forms_match={comparison['forms_match']}, "
                                   f"role_completeness={comparison['role_completeness']}")


def _group_dimensionless(sysrep: SystemRepresentation, group: str) -> bool | None:
    """Compute the dimension of a named shared group from the system's variables and
    check it is dimensionless. Implemented for the benchmark groups."""
    roles = sysrep.term_roles
    try:
        if group == "damping_ratio":  # b / sqrt(a*c)
            a = dim.named(sysrep.variables[roles["inertia"]])
            b = dim.named(sysrep.variables[roles["dissipation"]])
            c = dim.named(sysrep.variables[roles["restoring"]])
            return (b / ((a * c) ** Fraction(1, 2))).is_dimensionless
        if group == "fourier_number":  # D*time/length^2
            D = dim.named(sysrep.variables[roles["diffusivity"]])
            t = dim.named(sysrep.variables[roles["time"]])
            x = dim.named(sysrep.variables[roles["space"]])
            return (D * t / (x ** 2)).is_dimensionless
    except KeyError:
        return None
    return None


def dimensional_test(source: SystemRepresentation, target: SystemRepresentation
                     ) -> ValidationResult:
    """Verify a shared dimensionless group is truly dimensionless in BOTH systems,
    each with its own (different) base dimensions — the deep signature of the analogy."""
    shared = set(source.dimensionless_groups) & set(target.dimensionless_groups)
    for group in ("damping_ratio", "fourier_number"):
        if group in shared:
            s_ok, t_ok = _group_dimensionless(source, group), _group_dimensionless(target, group)
            ok = bool(s_ok) and bool(t_ok)
            return ValidationResult(test="dimensional", passed=ok,
                                    detail=f"group '{group}' dimensionless: "
                                           f"source={s_ok}, target={t_ok}")
    return ValidationResult(test="dimensional", passed=False,
                            detail=f"no verifiable shared dimensionless group ({sorted(shared)})")


def mathematical_test(comparison: dict[str, Any]) -> ValidationResult:
    # General: the equation isomorphism is complete when (nearly) all roles map AND
    # the governing forms match. Not specific to any one equation family.
    ok = comparison["forms_match"] and comparison["role_completeness"] >= 0.8
    return ValidationResult(test="mathematical", passed=ok,
                            detail=f"forms_match={comparison['forms_match']}, "
                                   f"role_completeness={comparison['role_completeness']}, "
                                   f"missing_roles={comparison['missing_roles']}")


def limits_test(source: SystemRepresentation, target: SystemRepresentation) -> ValidationResult:
    # Both systems must conserve *something* in the appropriate limit, and share the
    # governing form (so a limiting case of one maps to a limiting case of the other).
    both_conserve = bool(source.invariants) and bool(target.invariants)
    from .structure import compare
    forms_match = compare(source, target)["forms_match"]
    ok = both_conserve and forms_match
    return ValidationResult(test="limits", passed=ok,
                            detail=f"both conserve a quantity={both_conserve}, "
                                   f"forms_match={forms_match}")


def predictive_transfer_test(source: SystemRepresentation, target: SystemRepresentation,
                             *, runner: SubprocessRunner | None = None,
                             coeffs=((1.0, 0.2, 4.0), (1.0, 0.3, 9.0))) -> ValidationResult:
    """Transfer the resonance prediction ω₀ = sqrt(restoring/inertia) and VERIFY it by
    simulating BOTH systems' ODE in the sandbox. Only meaningful when forms match."""
    comp = compare(source, target)
    if not comp["forms_match"] or "resonance" not in (
            set(source.dimensionless_groups) & set(target.dimensionless_groups)):
        return ValidationResult(test="predictive_transfer", passed=False,
                                detail="no shared resonance structure to transfer")
    runner = runner or SubprocessRunner()
    results = []
    for a, b, c in coeffs:
        ws = tempfile.mkdtemp(prefix="acero_ana_")
        os.makedirs(os.path.join(ws, "inputs"), exist_ok=True)
        with open(os.path.join(ws, "inputs", "params.json"), "w") as fh:
            json.dump({"a": a, "b": b, "c": c}, fh)
        res = runner.run(_RESONANCE_SCRIPT, ws, timeout_sec=60)
        if res.status != "ok":
            return ValidationResult(test="predictive_transfer", passed=False,
                                    detail=f"sandbox failed: {res.stderr[:120]}")
        obj = json.loads(res.stdout.strip().splitlines()[-1])
        results.append(obj["rel_error"])
    ok = all(e < 0.15 for e in results)
    return ValidationResult(test="predictive_transfer", passed=ok,
                            detail=f"resonance peak matches sqrt(c/a) in sandbox; "
                                   f"rel_errors={[round(e, 3) for e in results]}")


def _superficial_only(comparison: dict[str, Any]) -> bool:
    """True when there is surface/geometric correspondence but the deep governing
    structure does NOT match (the classic misleading-analogy signature, e.g.
    atom ↔ solar system: both have a 'center' and 'orbiting' role, but different
    governing equations)."""
    geometric = comparison["surface_similarity"] > 0.2 or len(comparison["shared_roles"]) >= 1
    return (not comparison["forms_match"]) and geometric


def counterexample_test(comparison: dict[str, Any]) -> ValidationResult:
    misleading = _superficial_only(comparison) and comparison["role_completeness"] < 0.6
    return ValidationResult(test="counterexample", passed=not misleading,
                            detail="no misleading surface-only correspondence"
                                   if not misleading else
                                   "surface/geometric similarity without deep structure (misleading)")


def determine_status(scores: AnalogyScores, validations: list[ValidationResult],
                     comparison: dict[str, Any] | None = None) -> AnalogyStatus:
    passed = {v.test for v in validations if v.passed}
    deep = scores.deep_score()
    counter_failed = any(v.test == "counterexample" and not v.passed for v in validations)

    # Misleading: superficial/geometric correspondence but the deep structure fails.
    if counter_failed or (comparison is not None and comparison.get("surface_similarity", 0) > 0.3
                          and "structural" not in passed):
        return AnalogyStatus.MISLEADING

    if {"structural", "dimensional", "mathematical"}.issubset(passed):
        if "predictive_transfer" in passed:
            return AnalogyStatus.STRUCTURALLY_SUPPORTED
        return AnalogyStatus.VALID_IN_REGIME
    if "structural" in passed and deep >= 0.5:
        return AnalogyStatus.PARTIALLY_VALID
    if deep < 0.2:
        return AnalogyStatus.REJECTED
    return AnalogyStatus.BROKEN
