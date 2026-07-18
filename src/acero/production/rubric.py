"""Production-readiness rubric (100 points) + scoring rules.

Encodes the weighted rubric (categories A–J) and the hard scoring rules that CAP a
category or the global score in the absence of executed evidence. The rules exist
precisely so a high score cannot be claimed on intuition, code volume, or a green
local `make verify` — evidence is required, and several ceilings can only be lifted
by a real deployment, an independent CI run, and a real external human review.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    title: str
    max_points: float


# A–J with the exact weights from the production rubric (total = 100).
CATEGORIES: tuple[Category, ...] = (
    Category("A", "Architecture & integrity", 10),
    Category("B", "Quality & tests", 12),
    Category("C", "Security", 15),
    Category("D", "Reliability & operations", 12),
    Category("E", "Product & UX", 10),
    Category("F", "Scientific rigor", 15),
    Category("G", "Data & provenance", 8),
    Category("H", "CI/CD & deployment", 8),
    Category("I", "Maintainability & docs", 5),
    Category("J", "External validation & governance", 5),
)

TOTAL_POINTS = sum(c.max_points for c in CATEGORIES)  # 100

# Targets required for the ≥95 goal (per category).
TARGETS = {
    "C": 13.5,   # security
    "F": 14.0,   # scientific rigor
    "D": 11.0,   # reliability
    "B": 11.0,   # quality
    "H": 7.0,    # CI/CD
}

GOAL_TOTAL = 95.0


@dataclass
class CategoryScore:
    key: str
    awarded: float
    evidence: str
    has_executed_evidence: bool = True
    relies_on_mocks_for_main_flow: bool = False

    def capped(self, cat: Category) -> tuple[float, list[str]]:
        """Apply per-category evidence caps (rules 1 & 2). Returns (points, notes)."""
        notes: list[str] = []
        pts = min(self.awarded, cat.max_points)
        # Rule 1: no category > 80% without executed evidence.
        if not self.has_executed_evidence:
            cap = 0.8 * cat.max_points
            if pts > cap:
                notes.append("rule1: capped to 80% (no executed evidence)")
                pts = cap
        # Rule 2: no category > 50% if its MAIN flow depends on mocks.
        if self.relies_on_mocks_for_main_flow:
            cap = 0.5 * cat.max_points
            if pts > cap:
                notes.append("rule2: capped to 50% (mocked main flow)")
                pts = cap
        return round(pts, 2), notes


# The hard rules that gate specific categories / the global score. These are
# checked against booleans supplied by the audit (real, discoverable facts).
def apply_rules(scores: dict[str, CategoryScore], facts: dict[str, bool]
                ) -> tuple[dict[str, float], list[str], list[str]]:
    """Return (category_points, applied_notes, global_blockers)."""
    notes: list[str] = []
    blockers: list[str] = []
    by_key = {c.key: c for c in CATEGORIES}
    points: dict[str, float] = {}
    for key, cs in scores.items():
        pts, cnotes = cs.capped(by_key[key])
        points[key] = pts
        notes.extend(f"{key}: {n}" for n in cnotes)

    # Rule 3: security ≤ 12/15 without dynamic tests on the REAL deployment.
    if not facts.get("dynamic_security_on_deploy") and points.get("C", 0) > 12.0:
        points["C"] = 12.0
        notes.append("rule3: security capped to 12/15 (no dynamic tests on real deploy)")
    # Rule 4: CI/CD ≤ 5/8 without an independently executed pipeline.
    if not facts.get("independent_ci_run") and points.get("H", 0) > 5.0:
        points["H"] = 5.0
        notes.append("rule4: CI/CD capped to 5/8 (no independent pipeline run)")
    # Rule 5: external validation ≤ 3/5 if no external person reviewed a dossier.
    if not facts.get("external_review_done") and points.get("J", 0) > 3.0:
        points["J"] = 3.0
        notes.append("rule5: external validation capped to 3/5 (no external reviewer)")

    # Rule 6: an open CRITICAL finding caps the GLOBAL score at 89.
    if facts.get("open_critical_finding"):
        blockers.append("rule6: open CRITICAL finding — global score capped at 89")
    # Rules 7/8/9: production/science blockers.
    if facts.get("open_critical_security"):
        blockers.append("rule7: open CRITICAL security finding — blocks production")
    if not facts.get("backup_restore_proven"):
        blockers.append("rule8: backup/restore not proven — blocks production")
    if facts.get("scientific_gate_bypass"):
        blockers.append("rule9: scientific gate bypass — blocks scientific production")

    return points, notes, blockers


# Rule 10 preconditions for a ≥95 score (all must hold).
RULE10_REQUIREMENTS = (
    "zero_critical_findings", "all_p0_gates", "deployment_tested", "rollback_tested",
    "ci_green", "dynamic_security", "real_e2e", "documentation", "independent_score_review",
)


def rule10_met(facts: dict[str, bool]) -> tuple[bool, list[str]]:
    missing = [r for r in RULE10_REQUIREMENTS if not facts.get(r)]
    return (not missing), missing
