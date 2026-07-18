"""Production score assembly + iteration records.

Combines per-category scores and discoverable facts, applies the rubric rules
(including the global CRITICAL cap and the Rule-10 ≥95 preconditions), and returns
an honest total. Iteration records are append-only; criteria are never changed
retroactively to inflate a score.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from . import rubric


@dataclass
class ProductionScore:
    total: float
    category_points: dict[str, float]
    max_by_category: dict[str, float]
    applied_notes: list[str]
    global_blockers: list[str]
    rule10_met: bool
    rule10_missing: list[str]
    goal: float = rubric.GOAL_TOTAL

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def score(scores: dict[str, rubric.CategoryScore], facts: dict[str, bool]) -> ProductionScore:
    points, notes, blockers = rubric.apply_rules(scores, facts)
    total = round(sum(points.values()), 2)

    # Rule 6: an open CRITICAL finding caps the GLOBAL total at 89.
    if facts.get("open_critical_finding") and total > 89.0:
        total = 89.0
        notes.append("rule6 applied: total capped at 89 (open CRITICAL)")

    met, missing = rubric.rule10_met(facts)
    # A ≥95 total is only permitted if Rule 10 preconditions all hold.
    if total >= rubric.GOAL_TOTAL and not met:
        total = min(total, 94.9)
        notes.append(f"rule10: ≥95 requires {missing}; total held below 95")

    return ProductionScore(
        total=total,
        category_points={k: round(v, 2) for k, v in points.items()},
        max_by_category={c.key: c.max_points for c in rubric.CATEGORIES},
        applied_notes=notes, global_blockers=blockers,
        rule10_met=met, rule10_missing=missing)


@dataclass
class IterationRecord:
    iteration_number: int
    baseline_score: float
    findings: list[str]
    selected_improvements: list[str]
    implementation_commits: list[str]
    tests_added: list[str]
    tests_failed: list[str]
    security_findings: list[str]
    scientific_findings: list[str]
    production_findings: list[str]
    score_after: float
    remaining_blockers: list[str]
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
