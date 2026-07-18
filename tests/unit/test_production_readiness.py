"""Production-readiness scoring framework tests (evidence-based, honest caps)."""

from __future__ import annotations

from acero.production import rubric
from acero.production.audit import run_audit
from acero.production.rubric import CategoryScore
from acero.production.scoring import score


def test_rubric_totals_100():
    assert rubric.TOTAL_POINTS == 100
    assert {c.key for c in rubric.CATEGORIES} == set("ABCDEFGHIJ")


def test_baseline_score_is_honest_and_below_95():
    r = run_audit()
    s = r["score"]
    assert 0 < s["total"] < 95            # cannot reach 95 un-deployed / un-reviewed
    assert s["rule10_met"] is False
    assert set(s["rule10_missing"]) >= {"deployment_tested", "ci_green", "dynamic_security"}


def test_rule3_caps_security_without_dynamic_tests():
    cats = {"C": CategoryScore("C", 15.0, "perfect static")}
    s = score(cats, {**_facts(), "dynamic_security_on_deploy": False})
    assert s.category_points["C"] == 12.0


def test_rule4_caps_ci_without_independent_run():
    cats = {"H": CategoryScore("H", 8.0, "great local")}
    s = score(cats, {**_facts(), "independent_ci_run": False})
    assert s.category_points["H"] == 5.0


def test_rule5_caps_external_validation_without_reviewer():
    cats = {"J": CategoryScore("J", 5.0, "bundles ready")}
    s = score(cats, {**_facts(), "external_review_done": False})
    assert s.category_points["J"] == 3.0


def test_rule6_open_critical_caps_total_at_89():
    cats = {c.key: CategoryScore(c.key, c.max_points, "max") for c in rubric.CATEGORIES}
    facts = {**_facts(), "open_critical_finding": True,
             "dynamic_security_on_deploy": True, "independent_ci_run": True,
             "external_review_done": True}
    s = score(cats, facts)
    assert s.total <= 89.0


def test_rule1_caps_category_without_executed_evidence():
    cats = {"A": CategoryScore("A", 10.0, "claims only", has_executed_evidence=False)}
    s = score(cats, _facts())
    assert s.category_points["A"] == 8.0        # 80% of 10


def test_rule2_caps_category_with_mocked_main_flow():
    cats = {"B": CategoryScore("B", 12.0, "mocked", relies_on_mocks_for_main_flow=True)}
    s = score(cats, _facts())
    assert s.category_points["B"] == 6.0        # 50% of 12


def test_ninety_five_requires_all_rule10_preconditions():
    cats = {c.key: CategoryScore(c.key, c.max_points, "max") for c in rubric.CATEGORIES}
    ok = {k: True for k in (
        "dynamic_security_on_deploy", "independent_ci_run", "external_review_done",
        "backup_restore_proven", "zero_critical_findings", "all_p0_gates",
        "deployment_tested", "rollback_tested", "ci_green", "dynamic_security",
        "real_e2e", "documentation", "independent_score_review")}
    assert score(cats, ok).total >= 95.0        # all preconditions -> 95 allowed
    # remove one precondition -> held below 95
    held = score(cats, {**ok, "deployment_tested": False})
    assert held.total < 95.0


def _facts() -> dict[str, bool]:
    return {"backup_restore_proven": True}
