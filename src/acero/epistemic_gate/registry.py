"""Central registry of gate rules, keyed by stage and versioned.

A Codex finding becomes a rule ONLY through ``promote_codex_finding``, which refuses
unless the finding ships a real, callable checker (with a test the caller must add). Codex
can never approve, block by itself, or certify a conclusion.
"""

from __future__ import annotations

from ..core.clock import now_iso
from .models import Checker, GateRule, Severity, Stage
from .rules import (
    cognitive,
    execution,
    experiment,
    hypothesis,
    inference,
    literature,
    publication,
    understanding,
    world_model,
)

_STAGE_RULES: dict[Stage, list[GateRule]] = {
    Stage.LITERATURE: list(literature.RULES),
    Stage.HYPOTHESIS: list(hypothesis.RULES),
    Stage.EXPERIMENT_DESIGN: list(experiment.RULES),
    Stage.EXECUTION: list(execution.RULES),
    Stage.INFERENCE: list(inference.RULES),
    Stage.ANALOGY: list(cognitive.ANALOGY_RULES),
    Stage.DERIVATION: list(cognitive.DERIVATION_RULES),
    Stage.WORLD_MODEL_UPDATE: list(world_model.RULES),
    Stage.HUMAN_REVIEW: list(understanding.RULES),
    Stage.PUBLICATION: list(publication.RULES),
}


class GateRegistry:
    def __init__(self) -> None:
        # deep-ish copy so promotions don't mutate the module-level defaults
        self._rules: dict[Stage, list[GateRule]] = {
            s: list(rs) for s, rs in _STAGE_RULES.items()}

    def rules_for(self, stage: Stage) -> list[GateRule]:
        return list(self._rules.get(stage, []))

    def all_rules(self) -> list[GateRule]:
        return [r for rs in self._rules.values() for r in rs]

    def rule_ids(self, stage: Stage | None = None) -> list[str]:
        rules = self.rules_for(stage) if stage else self.all_rules()
        return [r.id for r in rules]

    def promote_codex_finding(
        self, *, rule_id: str, stage: Stage, description: str, checker: Checker | None,
        severity: Severity = Severity.BLOCKER, remediation: str = "",
        has_test: bool = False,
    ) -> GateRule:
        """Turn a Codex finding into a real rule — only if it is verifiable.

        Requires a callable ``checker`` AND ``has_test=True`` (the caller must have added a
        regression test). Otherwise the promotion is refused: Codex cannot legislate.
        """
        if checker is None or not callable(checker):
            raise ValueError("cannot promote a Codex finding without a callable checker")
        if not has_test:
            raise ValueError("cannot promote a Codex finding without a regression test")
        version = f"codex-{now_iso()[:10]}"
        r = GateRule(id=rule_id, stage=stage, severity=severity, description=description,
                     checker=checker, failure_message=description, remediation=remediation,
                     deterministic=True, source="codex-promoted", version=version)
        self._rules.setdefault(stage, []).append(r)
        return r


DEFAULT_REGISTRY = GateRegistry()
