"""Bridge existing policies into gate results.

A policy violation (cost, security, publication, data, autonomy) must ALSO appear as a
gate result, so a single place answers "may this proceed?". We call the existing
PolicyGuard and translate a PolicyViolation into a BLOCKED GateResult — we do not restate
the policy logic here, avoiding contradictory duplicate rules (9.29).
"""

from __future__ import annotations

from ..core.clock import now_iso
from ..policies.guard import PolicyGuard
from .models import GateOutcome, GateResult, RuleResult, Severity, Stage


def _blocked(stage: Stage, rule_id: str, detail: str) -> GateResult:
    return GateResult(
        stage=stage.value, outcome=GateOutcome.BLOCKED,
        results=[RuleResult(rule_id, stage.value, Severity.BLOCKER.value, False,
                            detail=detail, remediation="obtain human approval / adjust policy")],
        responsible="policy", timestamp=now_iso())


def _passed(stage: Stage, rule_id: str) -> GateResult:
    return GateResult(
        stage=stage.value, outcome=GateOutcome.PASS,
        results=[RuleResult(rule_id, stage.value, Severity.BLOCKER.value, True)],
        responsible="policy", timestamp=now_iso())


def check_publication_policy(guard: PolicyGuard, *, human_reviewed: bool) -> GateResult:
    from ..core.errors import PolicyViolation
    try:
        guard.check_publication(human_reviewed)
        return _passed(Stage.PUBLICATION, "policy_publication")
    except PolicyViolation as exc:
        return _blocked(Stage.PUBLICATION, "policy_publication", str(exc))


def check_autonomy_policy(guard: PolicyGuard, action: str, stage: Stage) -> GateResult:
    from ..core.errors import PolicyViolation
    try:
        guard.require_autonomous(action)
        return _passed(stage, "policy_autonomy")
    except PolicyViolation as exc:
        # Human-required is an escalation, not a hard block.
        res = _blocked(stage, "policy_autonomy", str(exc))
        res.outcome = GateOutcome.ESCALATE_TO_HUMAN
        res.results[0].severity = Severity.WARNING.value
        return res


def check_research_domain_policy(guard: PolicyGuard, domain: str) -> GateResult:
    from ..core.errors import PolicyViolation
    try:
        guard.check_research_domain(domain)
        return _passed(Stage.EXPERIMENT_DESIGN, "policy_research_safety")
    except PolicyViolation as exc:
        return _blocked(Stage.EXPERIMENT_DESIGN, "policy_research_safety", str(exc))
