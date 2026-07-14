"""Experiment-design-stage gate rules (9.19)."""

from __future__ import annotations

from ..models import GateRule, Stage
from .common import rule

S = Stage.EXPERIMENT_DESIGN

RULES: list[GateRule] = [
    rule("has_baseline", S, "has_baseline", expect=True,
         detail="no baseline defined",
         remediation="add a baseline to compare against"),
    rule("has_controls", S, "has_controls", expect=True,
         detail="no control defined",
         remediation="add appropriate controls"),
    rule("metrics_prespecified", S, "metrics_defined_after", expect=False,
         detail="metrics were defined after seeing results (HARKing)",
         remediation="prespecify metrics in the preregistration"),
    rule("is_discriminating", S, "is_discriminating", expect=True,
         detail="experiment cannot discriminate between competing hypotheses",
         remediation="design an experiment whose outcome separates the hypotheses"),
    rule("has_budget", S, "has_budget", expect=True,
         detail="no budget defined",
         remediation="declare a resource/time budget"),
    rule("has_stopping_rule", S, "has_stopping_rule", expect=True,
         detail="no stopping rule defined",
         remediation="declare a stopping rule"),
    rule("confounders_addressed", S, "known_confounders_ignored", expect=False,
         detail="known confounders are ignored",
         remediation="control or measure the known confounders"),
    rule("outcome_can_weaken", S, "outcome_cannot_weaken_any_hypothesis", expect=False,
         detail="no possible outcome would weaken any hypothesis",
         remediation="ensure at least one outcome is disconfirming"),
]
