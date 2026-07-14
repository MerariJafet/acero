"""World-Model-update-stage gate rules (9.24)."""

from __future__ import annotations

from ..models import Checker, GateRule, NotEvaluable, Severity, Stage
from .common import rule

S = Stage.WORLD_MODEL_UPDATE


def _confidence_below_one() -> Checker:
    def check(a: dict[str, object]) -> str | None:
        if "belief_confidence" not in a:
            raise NotEvaluable("missing input 'belief_confidence'")
        c = a["belief_confidence"]
        assert isinstance(c, (int, float))
        return "belief confidence is 1.0 (absolute truth is not allowed)" if c >= 1.0 else None
    return check


RULES: list[GateRule] = [
    rule("not_codex_only", S, "updated_by_codex_only", expect=False,
         detail="a belief was updated solely on Codex output",
         remediation="require verifiable evidence, not LLM output, to update a belief"),
    rule("evidence_has_provenance", S, "evidence_has_provenance", expect=True,
         detail="evidence for the update has no provenance",
         remediation="attach provenance to the evidence"),
    rule("contradiction_not_ignored", S, "contradiction_ignored", expect=False,
         detail="a contradiction with existing beliefs is ignored",
         remediation="record and reconcile the contradiction"),
    rule("no_history_overwrite", S, "overwrites_history", expect=False,
         detail="belief history would be overwritten",
         remediation="version the belief instead of overwriting"),
    GateRule(id="confidence_below_one", stage=S, severity=Severity.BLOCKER,
             description="belief confidence must be < 1.0",
             checker=_confidence_below_one(), inputs=("belief_confidence",),
             failure_message="confidence = 1.0", remediation="cap confidence below 1.0"),
    rule("independent_replication", S, "dependent_counted_as_independent", expect=False,
         detail="dependent evidence is counted as independent replication",
         remediation="do not double-count dependent evidence"),
    rule("simulation_not_physical", S, "simulation_as_physical_proof", expect=False,
         detail="a simulation result is presented as physical proof",
         remediation="state that simulation is not physical evidence"),
    rule("claim_has_limitations", S, "claim_without_limitations", expect=False,
         detail="the claim has no stated limitations", severity=Severity.WARNING,
         remediation="state the limitations of the claim"),
]
