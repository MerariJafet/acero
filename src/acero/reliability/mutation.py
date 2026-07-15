"""Scientific mutation testing (Sprint 11).

Beyond code mutation: mutate the SCIENCE of a clean artifact (change units, remove the
baseline, flip labels, drop a control, edit a pre-registered prediction, swap the dataset
after the fact, replace a source, duplicate evidence, hide a negative result) and confirm the
gate (or a detector) catches each mutation. A mutation that survives is a reliability gap.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScientificMutation:
    id: str
    description: str
    # apply the mutation to a clean artifact and return the mutated one
    apply: Callable[[dict[str, Any]], dict[str, Any]]
    # the detector that should catch it (returns True if caught)
    detect: Callable[[dict[str, Any]], bool]


def _clean_inference() -> dict[str, Any]:
    from ..epistemic_gate.rules.inference import artifact_from_gate_input
    from ..inference.audit.gate import GateInput
    return artifact_from_gate_input(GateInput())


def _inference_blocked(art: dict[str, Any]) -> bool:
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage
    return GlobalGate().check(Stage.INFERENCE, art).outcome == GateOutcome.BLOCKED


def _clean_experiment() -> dict[str, Any]:
    return {"has_baseline": True, "has_controls": True, "metrics_defined_after": False,
            "is_discriminating": True, "has_budget": True, "has_stopping_rule": True,
            "known_confounders_ignored": False, "outcome_cannot_weaken_any_hypothesis": False}


def _experiment_blocked(art: dict[str, Any]) -> bool:
    from ..epistemic_gate.engine import GlobalGate
    from ..epistemic_gate.models import GateOutcome, Stage
    return GlobalGate().check(Stage.EXPERIMENT_DESIGN, art).outcome == GateOutcome.BLOCKED


def mutations() -> list[ScientificMutation]:
    return [
        ScientificMutation(
            "change_units", "flip dimensional consistency",
            lambda a: {**a, "dimensions_valid": False}, _inference_blocked),
        ScientificMutation(
            "remove_baseline", "drop the baseline",
            lambda a: {**_clean_experiment(), "has_baseline": False}, _experiment_blocked),
        ScientificMutation(
            "remove_control", "drop a control",
            lambda a: {**_clean_experiment(), "has_controls": False}, _experiment_blocked),
        ScientificMutation(
            "edit_prereg", "edit a pre-registered prediction (HARKing)",
            lambda a: {**_clean_experiment(), "metrics_defined_after": True},
            _experiment_blocked),
        ScientificMutation(
            "swap_dataset", "swap the dataset after the fact (leakage)",
            lambda a: {**a, "train_test_disjoint": False}, _inference_blocked),
        ScientificMutation(
            "hide_negative", "hide a negative result",
            lambda a: {**a, "negatives_preserved": False}, _inference_blocked),
        ScientificMutation(
            "codex_as_evidence", "cite Codex as evidence",
            lambda a: {**a, "codex_treated_as_evidence": True}, _inference_blocked),
        ScientificMutation(
            "break_repro", "make the result irreproducible",
            lambda a: {**a, "reproduced": False}, _inference_blocked),
    ]


@dataclass
class MutationResult:
    id: str
    description: str
    caught: bool


@dataclass
class MutationReport:
    results: list[MutationResult] = field(default_factory=list)

    @property
    def survived(self) -> list[str]:
        return [r.id for r in self.results if not r.caught]

    def as_dict(self) -> dict[str, Any]:
        return {"n": len(self.results),
                "caught": sum(1 for r in self.results if r.caught),
                "survived": self.survived,
                "results": [{"id": r.id, "caught": r.caught} for r in self.results]}


def run_mutation_testing(muts: list[ScientificMutation] | None = None) -> MutationReport:
    muts = muts or mutations()
    base = _clean_inference()
    out: list[MutationResult] = []
    for m in muts:
        mutated = m.apply(base)
        try:
            caught = m.detect(mutated)
        except Exception:  # noqa: BLE001 - a detector error means survived
            caught = False
        out.append(MutationResult(m.id, m.description, caught))
    return MutationReport(out)
