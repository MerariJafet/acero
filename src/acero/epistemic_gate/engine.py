"""The Global Epistemic Gate engine.

``check`` runs every rule of a stage against an artifact and computes an outcome.
``run_pipeline`` walks the canonical stage order and stops accepting knowledge at the
first BLOCKED stage. Codex findings are advisory: they can only raise WARNINGs unless they
name an existing rule id in the registry (mirroring the inference gate's discipline).
"""

from __future__ import annotations

from typing import Any

from .models import (
    GateOutcome,
    GateResult,
    NotEvaluable,
    RuleResult,
    Severity,
    Stage,
)
from .registry import DEFAULT_REGISTRY, GateRegistry

# Canonical pipeline order the gate governs.
PIPELINE: tuple[Stage, ...] = (
    Stage.LITERATURE, Stage.QUESTION, Stage.HYPOTHESIS, Stage.EXPERIMENT_DESIGN,
    Stage.EXECUTION, Stage.INFERENCE, Stage.ANALOGY, Stage.DERIVATION,
    Stage.WORLD_MODEL_UPDATE, Stage.HUMAN_REVIEW, Stage.PUBLICATION,
)


class GlobalGate:
    def __init__(self, registry: GateRegistry | None = None) -> None:
        self.registry = registry or DEFAULT_REGISTRY

    def check(self, stage: Stage, artifact: dict[str, Any], *,
              codex_findings: list[dict[str, Any]] | None = None,
              responsible: str = "system") -> GateResult:
        results: list[RuleResult] = []
        valid_ids = set(self.registry.rule_ids(stage))

        for r in self.registry.rules_for(stage):
            try:
                detail = r.checker(artifact)
            except NotEvaluable as exc:
                results.append(RuleResult(r.id, stage.value, r.severity.value, False,
                                          detail=str(exc), remediation=r.remediation,
                                          evaluable=False))
                continue
            results.append(RuleResult(
                r.id, stage.value, r.severity.value, passed=detail is None,
                detail=detail or "", remediation=r.remediation if detail else ""))

        # Codex advisory findings — promote to a blocker ONLY if they name a real rule.
        for cf in (codex_findings or []):
            rid = cf.get("rule", "")
            if rid in valid_ids:
                results.append(RuleResult(rid, stage.value, Severity.BLOCKER.value, False,
                                          detail=f"[codex-promoted] {cf.get('detail', '')}",
                                          remediation="verify and remediate"))
            else:
                results.append(RuleResult(
                    f"codex:{cf.get('concern', 'finding')}", stage.value,
                    Severity.WARNING.value, False, detail=cf.get("detail", ""),
                    evaluable=True))

        outcome = self._outcome(results, artifact)
        return GateResult(stage=stage.value, outcome=outcome, results=results,
                          responsible=responsible)

    def _outcome(self, results: list[RuleResult], artifact: dict[str, Any]
                 ) -> GateOutcome:
        has_blocker = any(not r.passed and r.severity == Severity.BLOCKER.value
                          and r.evaluable for r in results)
        if has_blocker:
            return GateOutcome.BLOCKED
        # Human-review comprehension can request a learning block.
        if artifact.get("comprehension_status") == "BLOCKED_FOR_LEARNING":
            return GateOutcome.BLOCKED_FOR_LEARNING
        if artifact.get("escalate_to_human"):
            return GateOutcome.ESCALATE_TO_HUMAN
        has_warning = any((not r.passed) or (not r.evaluable) for r in results)
        return GateOutcome.PASS_WITH_WARNINGS if has_warning else GateOutcome.PASS

    def run_pipeline(self, artifacts: dict[Stage, dict[str, Any]], *,
                     responsible: str = "system") -> dict[str, GateResult]:
        """Run the gate for each provided stage in canonical order.

        Stops governing further stages once a stage is BLOCKED (knowledge does not flow
        past a blocked gate), but still reports the stage that blocked.
        """
        out: dict[str, GateResult] = {}
        for stage in PIPELINE:
            if stage not in artifacts:
                continue
            res = self.check(stage, artifacts[stage], responsible=responsible)
            out[stage.value] = res
            if res.outcome == GateOutcome.BLOCKED:
                break
        return out
