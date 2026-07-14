"""Deterministic core of the hybrid grader — the authority.

Wraps the existing rubric grader (`assessment/grading.py`) and adds explicit concept
coverage. This layer alone can PASS or FAIL a response; the semantic layer only advises.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..assessment.grading import GradeResult, grade


@dataclass
class DeterministicResult:
    score: float
    matched: list[str]
    missing: list[str]
    red_flags: list[str]
    concept_coverage: float
    rubric_version: str = "v1"
    extra: dict[str, float] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.score >= 0.7 and not self.red_flags


def evaluate(response: str, expected_elements: list[str], *,
             required_concepts: list[str] | None = None,
             forbidden_elements: list[str] | None = None,
             rubric_version: str = "v1") -> DeterministicResult:
    g: GradeResult = grade(response, expected_elements,
                           forbidden_elements=forbidden_elements,
                           rubric_version=rubric_version)
    req = required_concepts or []
    low = response.lower()
    covered = [c for c in req if c.lower() in low]
    coverage = len(covered) / len(req) if req else 1.0
    return DeterministicResult(
        score=g.score, matched=g.matched, missing=g.missing, red_flags=g.red_flags,
        concept_coverage=round(coverage, 4), rubric_version=g.rubric_version)
