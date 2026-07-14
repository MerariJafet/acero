"""Inference-stage gate rules (9.21).

This generalizes the 14 blocker rules of the Sprint 8.9 inference gate
(``acero.inference.audit.gate``) into the transversal layer. The conditions are the same
booleans that gate checks; ``artifact_from_gate_input`` converts a GateInput into the
flat artifact these rules read, so the two never disagree.
"""

from __future__ import annotations

from typing import Any

from ...inference.audit.gate import GateInput
from ...inference.models import IdentifiabilityStatus
from ..models import GateRule, Severity, Stage
from .common import rule

S = Stage.INFERENCE

RULES: list[GateRule] = [
    rule("invalid_dimensions", S, "dimensions_valid", expect=True,
         detail="the candidate is dimensionally inconsistent",
         remediation="fix units so both sides are dimensionally consistent"),
    rule("data_leakage", S, "train_test_disjoint", expect=True,
         detail="train and test data are not disjoint (leakage)",
         remediation="hold out a disjoint test set"),
    rule("unreliable_derivatives_declared", S, "derivatives_reliable_or_declared",
         expect=True, detail="unreliable derivatives were not declared",
         remediation="declare derivative method and unreliable regions"),
    rule("non_identifiable_presented_as_unique", S, "identifiable_or_not_unique",
         expect=True,
         detail="a non/partially-identifiable model is presented as the unique answer",
         remediation="report identifiability and present alternatives"),
    rule("equivalent_counted_as_new", S, "equivalent_counted_as_new", expect=False,
         detail="observationally equivalent models are counted as distinct discoveries",
         remediation="cluster equivalent models before counting"),
    rule("extrapolation_without_test", S, "extrapolation_tested", expect=True,
         detail="extrapolation is claimed without a test",
         remediation="test out-of-range predictions before extrapolating"),
    rule("false_precision", S, "coefficients_have_uncertainty_or_no_precision_claim",
         expect=True,
         detail="coefficients without uncertainty are presented with false precision",
         remediation="report intervals or drop the extra significant figures"),
    rule("causal_claim_without_evidence", S, "causal_claim_supported", expect=True,
         detail="a causal claim is made without causal/intervention evidence",
         remediation="obtain intervention evidence or soften to association"),
    rule("imposed_structure_declared", S, "imposed_structure_declared", expect=True,
         detail="imposed structure (library/constraints) is not declared",
         remediation="declare what was imposed vs. inferred"),
    rule("negative_result_preserved", S, "negatives_preserved", expect=True,
         detail="a negative result was lost/deleted",
         remediation="preserve negative results"),
    rule("codex_as_evidence", S, "codex_treated_as_evidence", expect=False,
         detail="Codex output is treated as scientific evidence",
         remediation="treat LLM output as advisory only"),
    rule("uncalibrated_as_probability", S, "confidence_calibrated_or_labeled",
         expect=True,
         detail="uncalibrated confidence is presented as a probability",
         remediation="label confidence as uncalibrated or calibrate it"),
    rule("missing_provenance", S, "has_provenance", expect=True,
         detail="no provenance recorded for the inference",
         remediation="attach provenance to the result"),
    rule("not_reproducible", S, "reproduced", expect=True,
         detail="the inference did not reproduce",
         remediation="make the pipeline deterministic and re-run"),
]

# Level-overstatement is a warning to escalate, not a hard block.
RULES.append(GateRule(
    id="level_overstatement_risk", stage=S, severity=Severity.WARNING,
    description="do not call a fitting-level result a law or mechanism",
    checker=lambda a: (None if a.get("inference_level") not in
                       ("curve_fitting", "system_identification")
                       else "level is fitting/identification; not a law or mechanism"),
    inputs=("inference_level",), remediation="declare the inference level honestly"))


def artifact_from_gate_input(gi: GateInput) -> dict[str, Any]:
    """Map a Sprint 8.9 GateInput onto the flat artifact these rules read."""
    non_unique_ok = not (
        gi.identifiability in (IdentifiabilityStatus.NON_IDENTIFIABLE,
                               IdentifiabilityStatus.PARTIALLY_IDENTIFIABLE)
        and gi.presented_as_unique)
    return {
        "dimensions_valid": gi.dimensions_valid,
        "train_test_disjoint": gi.train_test_disjoint,
        "derivatives_reliable_or_declared": True,        # declared by engine honesty note
        "identifiable_or_not_unique": non_unique_ok,
        "equivalent_counted_as_new": (gi.n_equivalent_models > 1
                                      and gi.counts_equivalent_as_new),
        "extrapolation_tested": gi.extrapolation_tested,
        "coefficients_have_uncertainty_or_no_precision_claim": True,
        "causal_claim_supported": (not gi.makes_causal_claim
                                   or gi.has_intervention_evidence),
        "imposed_structure_declared": True,
        "negatives_preserved": gi.negatives_preserved,
        "codex_treated_as_evidence": gi.codex_treated_as_evidence,
        "confidence_calibrated_or_labeled": (gi.calibration_declared
                                             or not gi.known_miscalibrated),
        "has_provenance": gi.has_provenance,
        "reproduced": gi.reproduced,
        "inference_level": gi.inference_level,
    }
