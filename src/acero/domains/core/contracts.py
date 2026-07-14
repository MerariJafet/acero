"""The Scientific Domain contract.

A domain lab is NOT a bag of formulas: it declares an ontology, concepts, units, scales,
models, term libraries, tools, datasets, validations, gate rules, a safety class, a
benchmark suite, learning requirements, and — crucially — what it CANNOT do and which
results need institutional collaboration. Every domain output is classified so a
simulation is never presented as physical validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def to_native(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays to native Python for JSON serialization.

    Lab benchmarks compute with numpy; this keeps their public dicts JSON-safe without
    each case having to remember to cast."""
    if isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if hasattr(obj, "item") and callable(getattr(obj, "item", None)):
        try:
            return obj.item()          # numpy scalar → python scalar
        except (ValueError, TypeError):
            return obj
    return obj


class DomainResultClass(str, Enum):
    """How strong is a domain output? ACERO must never inflate one into another."""

    CALCULATION = "CALCULATION"
    SIMULATION = "SIMULATION"
    STATISTICAL_ASSOCIATION = "STATISTICAL_ASSOCIATION"
    MODEL_FIT = "MODEL_FIT"
    STRUCTURE_INFERENCE = "STRUCTURE_INFERENCE"
    MECHANISTIC_HYPOTHESIS = "MECHANISTIC_HYPOTHESIS"
    CAUSAL_CLAIM = "CAUSAL_CLAIM"
    PHYSICAL_VALIDATION = "PHYSICAL_VALIDATION"
    BIOLOGICAL_VALIDATION = "BIOLOGICAL_VALIDATION"
    CHEMICAL_VALIDATION = "CHEMICAL_VALIDATION"


# Result classes ACERO can produce computationally. The *_VALIDATION classes require real
# experiments and are therefore NEVER produced by a computational lab.
COMPUTATIONAL_CLASSES = frozenset({
    DomainResultClass.CALCULATION, DomainResultClass.SIMULATION,
    DomainResultClass.STATISTICAL_ASSOCIATION, DomainResultClass.MODEL_FIT,
    DomainResultClass.STRUCTURE_INFERENCE, DomainResultClass.MECHANISTIC_HYPOTHESIS,
})
VALIDATION_CLASSES = frozenset({
    DomainResultClass.PHYSICAL_VALIDATION, DomainResultClass.BIOLOGICAL_VALIDATION,
    DomainResultClass.CHEMICAL_VALIDATION,
})


class SafetyClass(str, Enum):
    LOW = "low"                    # computational, public data
    RESTRICTED = "restricted"      # extra guards (e.g. genetics/chemistry)


@dataclass
class Concept:
    name: str
    definition: str
    variables: list[str] = field(default_factory=list)
    units: dict[str, str] = field(default_factory=dict)


@dataclass
class DomainModel:
    name: str
    equation: str
    assumptions: list[str] = field(default_factory=list)
    regime: str = ""
    result_class: DomainResultClass = DomainResultClass.MODEL_FIT


@dataclass
class DomainResult:
    """A classified domain output — the unit the gate inspects."""

    kind: str
    value: Any
    result_class: DomainResultClass
    units: dict[str, str] = field(default_factory=dict)
    regime: str = ""
    limitations: list[str] = field(default_factory=list)
    label: str = ""                # e.g. COMPUTATIONAL_PREDICTION_NOT_EXPERIMENTALLY_VALIDATED

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value,
                "result_class": self.result_class.value, "units": self.units,
                "regime": self.regime, "limitations": self.limitations,
                "label": self.label}


@dataclass
class DomainCapabilities:
    can_do: list[str]
    cannot_do: list[str]
    approximations: list[str]
    dependencies: list[str]
    risks: list[str]
    needs_collaboration: list[str]


@dataclass
class ScientificDomain:
    id: str
    name: str
    ontology: str
    concepts: list[Concept]
    units: dict[str, str]
    dimensions: dict[str, str]
    scales: dict[str, str]
    supported_problem_types: list[str]
    models: list[DomainModel]
    tools: list[str]
    solvers: list[str]
    datasets: list[str]
    validation_rules: list[str]
    gate_rule_ids: list[str]
    safety_class: SafetyClass
    capabilities: DomainCapabilities
    learning_requirement_kind: str = ""

    def capabilities_dict(self) -> dict[str, Any]:
        c = self.capabilities
        return {"can_do": c.can_do, "cannot_do": c.cannot_do,
                "approximations": c.approximations, "dependencies": c.dependencies,
                "risks": c.risks, "needs_collaboration": c.needs_collaboration}

    def info(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "ontology": self.ontology,
            "concepts": [c.name for c in self.concepts], "units": self.units,
            "scales": self.scales, "supported_problem_types": self.supported_problem_types,
            "models": [m.name for m in self.models], "tools": self.tools,
            "solvers": self.solvers, "datasets": self.datasets,
            "gate_rule_ids": self.gate_rule_ids, "safety_class": self.safety_class.value,
            "capabilities": self.capabilities_dict(),
        }


class DomainLab:
    """Base class for a domain lab: exposes the contract, benchmarks, and gate rules."""

    def domain(self) -> ScientificDomain:            # pragma: no cover - overridden
        raise NotImplementedError

    def benchmark(self) -> dict[str, Any]:           # pragma: no cover - overridden
        raise NotImplementedError

    def classify(self, kind: str) -> DomainResultClass:  # pragma: no cover - overridden
        raise NotImplementedError
