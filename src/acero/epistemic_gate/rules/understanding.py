"""Human-review-stage gate rules (9.25).

Verifies minimum comprehension, critical concepts, active misconceptions, a human
prediction, and a limitations review. It shows WHICH decision is being made and why it
matters — it does not turn the human into a rubber stamp, and never blocks low-risk work.
"""

from __future__ import annotations

from ..models import Checker, GateOutcome, GateRule, NotEvaluable, Severity, Stage
from .common import rule

S = Stage.HUMAN_REVIEW


def _comprehension_ok() -> Checker:
    def check(a: dict[str, object]) -> str | None:
        if "comprehension_status" not in a:
            raise NotEvaluable("missing input 'comprehension_status'")
        status = str(a["comprehension_status"])
        # A learning block is surfaced by the engine as BLOCKED_FOR_LEARNING (a distinct
        # outcome), not as a hard rule blocker — so this rule passes it through.
        if status in (GateOutcome.PASS.value, "PASS", "PASS_WITH_SUPPORT",
                      "HUMAN_OVERRIDE", "BLOCKED_FOR_LEARNING"):
            return None
        return f"comprehension gate is {status}"
    return check


RULES: list[GateRule] = [
    GateRule(id="minimum_comprehension", stage=S, severity=Severity.BLOCKER,
             description="human demonstrated minimum comprehension of the decision",
             checker=_comprehension_ok(), inputs=("comprehension_status",),
             failure_message="insufficient comprehension",
             remediation="complete the required assessments or record an override"),
    rule("critical_concepts_assessed", S, "critical_concepts_assessed", expect=True,
         detail="critical concepts for this decision were not assessed",
         remediation="assess the concepts the decision depends on"),
    rule("no_active_blocking_misconception", S, "active_blocking_misconception",
         expect=False,
         detail="an unresolved blocking misconception is present",
         remediation="resolve the misconception with new evidence"),
    rule("human_prediction_present", S, "human_prediction_present", expect=True,
         detail="no human prediction was recorded before the result",
         severity=Severity.WARNING,
         remediation="record a prediction before revealing the result"),
    rule("limitations_reviewed", S, "limitations_reviewed", expect=True,
         detail="the human did not review the limitations",
         remediation="review the stated limitations before approving"),
    rule("explicit_approval", S, "explicit_human_approval", expect=True,
         detail="no explicit human approval where required",
         remediation="require explicit human approval for this decision"),
]
