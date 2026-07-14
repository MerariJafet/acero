"""Cognitive-stage gate rules: analogy (9.22) and derivation (9.23)."""

from __future__ import annotations

from ..models import GateRule, Severity, Stage
from .common import rule

ANALOGY = Stage.ANALOGY
DERIVATION = Stage.DERIVATION

ANALOGY_RULES: list[GateRule] = [
    rule("surface_analogy_transfer", ANALOGY, "surface_only_used_for_transfer",
         expect=False,
         detail="a surface-only analogy is used to transfer conclusions",
         remediation="require structural support before transferring"),
    rule("analogy_units_compatible", ANALOGY, "units_compatible", expect=True,
         detail="analogy maps incompatible units",
         remediation="check dimensional compatibility of the mapping"),
    rule("broken_structure_declared", ANALOGY, "broken_structure_declared", expect=True,
         detail="broken structural correspondence is not declared",
         remediation="declare where the structural mapping breaks"),
    rule("prediction_transfer_tested", ANALOGY, "transferred_prediction_tested",
         expect=True,
         detail="a transferred prediction was not tested",
         remediation="verify the transferred prediction (e.g. in the sandbox)"),
    rule("regime_of_validity", ANALOGY, "has_regime_of_validity", expect=True,
         detail="analogy has no stated regime of validity",
         remediation="state the regime where the analogy holds"),
    rule("misleading_not_explanation", ANALOGY, "misleading_as_explanation", expect=False,
         detail="a misleading analogy is presented as an explanation",
         remediation="mark misleading analogies and give failure conditions"),
]

DERIVATION_RULES: list[GateRule] = [
    rule("valid_symbolic_steps", DERIVATION, "all_steps_valid", expect=True,
         detail="an invalid symbolic step is present",
         remediation="verify each step with SymPy"),
    rule("derivation_units_correct", DERIVATION, "units_correct", expect=True,
         detail="a derivation step has incorrect units",
         remediation="check units at each step"),
    rule("no_hidden_assumption", DERIVATION, "hidden_assumption", expect=False,
         detail="a hidden assumption is used", severity=Severity.WARNING,
         remediation="surface the assumption explicitly"),
    rule("unresolved_step_not_done", DERIVATION, "unresolved_presented_as_done",
         expect=False,
         detail="an unresolved step is presented as proven",
         remediation="mark unresolved steps; do not claim completion"),
    rule("dim_analysis_not_derivation", DERIVATION, "dimensional_as_full_derivation",
         expect=False,
         detail="dimensional analysis is presented as a full derivation",
         remediation="state that dimensional analysis gives scaling, not the constant"),
    rule("symmetry_not_proof", DERIVATION, "symmetry_conservation_as_proof", expect=False,
         detail="a symmetry→conservation association is presented as a complete proof",
         remediation="present Noether-inspired links as motivation, not proof"),
    rule("conclusion_within_premises", DERIVATION, "conclusion_stronger_than_premises",
         expect=False,
         detail="the conclusion is stronger than the premises",
         remediation="weaken the conclusion to what the premises support"),
]

RULES = ANALOGY_RULES + DERIVATION_RULES
