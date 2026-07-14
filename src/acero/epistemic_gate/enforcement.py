"""The inline enforcement barrier.

`enforce()` is the ONE place a protected scientific mutation goes through:

    validate → run gate rules → block-or-continue → mutate → record gate result +
    provenance

The mutation runs ONLY after the gate passes (or a valid override is recorded). On a
block, no mutation happens and a separate rejection record is kept (the attempt is never
lost). Non-overridable rules can never be bypassed. Codex never authorizes a mutation.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.clock import now_iso
from .engine import GlobalGate
from .exceptions import GateBlockedError, OverrideNotAllowed
from .middleware import GateMetrics, GateTrace
from .models import GateOutcome, GateResult, Stage
from .transaction import Transaction, enforcement_enabled, gate_context


class OverridePolicy(str, Enum):
    NO_OVERRIDE = "NO_OVERRIDE"
    HUMAN_OVERRIDE_ALLOWED = "HUMAN_OVERRIDE_ALLOWED"
    ADMIN_OVERRIDE = "ADMIN_OVERRIDE"
    REQUIRES_EXTERNAL_REVIEW = "REQUIRES_EXTERNAL_REVIEW"


# Rules that can NEVER be overridden — fabrication, unsafe execution, lost provenance,
# false authorship, deleting negatives, retroactive unrecorded edits.
NON_OVERRIDABLE_RULES: frozenset[str] = frozenset({
    "citation_exists", "fragment_supports_claim",          # invented citation
    "not_reproducible", "data_leakage",                    # fabricated / leaked result
    "no_secrets_exposed", "ran_in_sandbox", "network_authorized",  # unsafe execution
    "missing_provenance", "evidence_has_provenance",       # lost provenance
    "no_history_overwrite",                                # retroactive unrecorded edit
    "no_ai_authorship",                                    # false authorship
    "negative_result_preserved",                           # deleting negatives
    "codex_as_evidence", "not_codex_only",                 # Codex/LLM as evidence
    "confidence_below_one",                                # absolute-truth claim
    "harking",                                             # post-hoc hypothesis edit
    # publication-stage integrity (Codex-audit fix): never overridable
    "citations_verified", "results_reproducible",
    "discovery_human_reviewed", "central_conclusion_understood",
})


@dataclass
class Override:
    responsible: str
    reason: str
    risk: str
    rules_ignored: list[str]
    policy: OverridePolicy = OverridePolicy.HUMAN_OVERRIDE_ALLOWED
    scope: str = "single-action"
    expires_at: str | None = None
    timestamp: str = field(default_factory=now_iso)


@dataclass
class GateProtectedAction:
    action: str
    stage: str
    artifact: dict[str, Any]
    context: dict[str, Any]
    required_rules: list[str]
    gate_result: GateResult
    allowed: bool
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    override_policy: str = OverridePolicy.HUMAN_OVERRIDE_ALLOWED.value
    override: Override | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    action_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"action_id": self.action_id, "action": self.action, "stage": self.stage,
                "allowed": self.allowed, "outcome": self.gate_result.outcome.value,
                "blockers": self.blockers, "warnings": self.warnings,
                "override": self.override.__dict__ if self.override else None,
                "provenance": self.provenance}


class GateEnforcer:
    """Runs the gate inline and performs a mutation only if allowed."""

    def __init__(self, gate: GlobalGate | None = None,
                 metrics: GateMetrics | None = None,
                 trace: GateTrace | None = None,
                 rejection_sink: Callable[[GateProtectedAction], None] | None = None
                 ) -> None:
        self.gate = gate or GlobalGate()
        self.metrics = metrics or GateMetrics()
        self.trace = trace or GateTrace()
        self.rejection_sink = rejection_sink

    def enforce(
        self, *, action: str, stage: Stage, artifact: dict[str, Any],
        mutation: Callable[[], Any], context: dict[str, Any] | None = None,
        override: Override | None = None,
        override_policy: OverridePolicy = OverridePolicy.HUMAN_OVERRIDE_ALLOWED,
        codex_findings: list[dict[str, Any]] | None = None,
    ) -> tuple[GateProtectedAction, Any]:
        """Gate-then-mutate. Returns (protected_action, mutation_result).

        Raises GateBlockedError (no mutation) if blocked without a valid override, and
        OverrideNotAllowed if an override targets a non-overridable rule.
        """
        ctx = context or {}
        action_id = f"gpa_{uuid.uuid4().hex[:12]}"
        result = self.gate.check(stage, artifact, codex_findings=codex_findings,
                                 responsible=ctx.get("actor", "system"))
        blockers = [b.rule_id for b in result.blockers]
        warnings = [w.rule_id for w in result.warnings]
        gpa = GateProtectedAction(
            action=action, stage=stage.value, artifact=artifact, context=ctx,
            required_rules=self.gate.registry.rule_ids(stage), gate_result=result,
            allowed=False, warnings=warnings, blockers=blockers,
            override_policy=override_policy.value, action_id=action_id)

        self.metrics.record_evaluated(stage.value, result)

        blocked = result.outcome in (GateOutcome.BLOCKED, GateOutcome.BLOCKED_FOR_LEARNING)
        if blocked:
            gpa.allowed = self._resolve_override(gpa, override, override_policy)
            if not gpa.allowed:
                self.metrics.record_blocked(stage.value, blockers)
                self.trace.add(gpa)
                if self.rejection_sink:
                    self.rejection_sink(gpa)          # attempt is never lost
                raise GateBlockedError(action, result)
            self.metrics.record_override(stage.value)
        else:
            gpa.allowed = True
            if warnings:
                self.metrics.record_warning(stage.value)

        # Passed (or valid override): perform the mutation inside a gate context so guarded
        # persistence sees an open window; roll back on failure.
        txn = Transaction()
        with enforcement_enabled(), gate_context(action, stage.value, action_id):
            try:
                mutation_result = mutation()
                txn.commit()
            except Exception:
                txn.rollback()
                raise
        gpa.provenance = {"action_id": action_id, "outcome": result.outcome.value,
                          "timestamp": now_iso(),
                          "override": gpa.override.__dict__ if gpa.override else None}
        self.metrics.record_allowed(stage.value)
        self.trace.add(gpa)
        return gpa, mutation_result

    def _resolve_override(self, gpa: GateProtectedAction, override: Override | None,
                          policy: OverridePolicy) -> bool:
        if override is None or policy == OverridePolicy.NO_OVERRIDE:
            return False
        non_overridable = [r for r in gpa.blockers if r in NON_OVERRIDABLE_RULES]
        if non_overridable:
            raise OverrideNotAllowed(gpa.action, non_overridable)
        if not override.reason or not override.responsible:
            raise OverrideNotAllowed(gpa.action, ["override missing responsible/reason"])
        gpa.override = override
        return True
