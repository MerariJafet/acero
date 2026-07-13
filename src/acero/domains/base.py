"""Domain-plugin framework (Sprint 10 initial implementation).

Each scientific domain (physics, astronomy, genetics, chemistry) exposes:
  * declared units and allowed (computational-only) tools,
  * input validation,
  * deterministic simulators (CPU-only, no wet-lab),
  * a project template,
  * a self-benchmark with known-answer checks.

Hard rule: NO autonomous wet-lab, no physical/biological/chemical procedures.
Every plugin declares its scope and risks; `research_safety` policy forbids the
dangerous domains regardless of what a plugin might expose.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationResult:
    ok: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @classmethod
    def valid(cls) -> ValidationResult:
        return cls(ok=True)

    @classmethod
    def invalid(cls, field_: str, message: str) -> ValidationResult:
        return cls(ok=False, issues=[ValidationIssue(field_, message)])


@dataclass
class BenchmarkCase:
    name: str
    expected: float
    actual: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return math.isfinite(self.actual) and abs(self.actual - self.expected) <= self.tolerance


@dataclass
class BenchmarkResult:
    domain: str
    cases: list[BenchmarkCase] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.passed)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.passed == self.total

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "passed": self.passed,
            "total": self.total,
            "all_passed": self.all_passed,
            "cases": [
                {"name": c.name, "expected": c.expected, "actual": c.actual,
                 "tolerance": c.tolerance, "passed": c.passed}
                for c in self.cases
            ],
        }


class DomainPlugin(ABC):
    name: str
    domain: str
    units: dict[str, str]
    allowed_tools: list[str]
    risks: list[str]

    @abstractmethod
    def _simulators(self) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        ...

    def simulators(self) -> list[str]:
        return sorted(self._simulators())

    def simulate(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        sims = self._simulators()
        if name not in sims:
            raise KeyError(f"{self.name}: unknown simulator '{name}'. Have: {self.simulators()}")
        return sims[name](params)

    @abstractmethod
    def validate(self, kind: str, data: dict[str, Any]) -> ValidationResult:
        ...

    @abstractmethod
    def project_template(self) -> str:
        ...

    @abstractmethod
    def benchmark(self) -> BenchmarkResult:
        ...

    def info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "units": self.units,
            "allowed_tools": self.allowed_tools,
            "simulators": self.simulators(),
            "risks": self.risks,
            "wet_lab": False,
        }
