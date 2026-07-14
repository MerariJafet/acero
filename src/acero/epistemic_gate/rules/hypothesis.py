"""Hypothesis-stage gate rules (9.18)."""

from __future__ import annotations

from ..models import GateRule, Severity, Stage
from .common import rule

S = Stage.HYPOTHESIS

RULES: list[GateRule] = [
    rule("hypothesis_has_prediction", S, "has_prediction", expect=True,
         detail="hypothesis has no testable prediction",
         remediation="state at least one predicted observation"),
    rule("hypothesis_falsifiable", S, "falsifiable", expect=True,
         detail="hypothesis is not falsifiable but is presented as scientific",
         remediation="state a falsification condition"),
    rule("no_duplicate_alternative", S, "duplicate_as_alternative", expect=False,
         detail="a duplicate hypothesis is counted as a distinct alternative",
         remediation="deduplicate competing hypotheses"),
    rule("hypothesis_has_assumptions", S, "has_assumptions", expect=True,
         detail="hypothesis states no assumptions", severity=Severity.WARNING,
         remediation="list the assumptions the hypothesis relies on"),
    rule("novelty_searched", S, "novelty_claimed_without_search", expect=False,
         detail="novelty is claimed without a prior-work search",
         remediation="run a literature/World-Model search before claiming novelty"),
    rule("mechanism_has_observables", S, "mechanism_without_observables", expect=False,
         detail="a mechanism is proposed with no observable variables",
         remediation="tie the mechanism to observable variables"),
]
