"""Sprint 9 tests: the Global Epistemic Gate (registry, engine, rules, policy bridge)."""

from __future__ import annotations

import pytest

from acero.epistemic_gate.audit import rules_audit
from acero.epistemic_gate.engine import PIPELINE, GlobalGate
from acero.epistemic_gate.models import (
    GateOutcome,
    NotEvaluable,
    Severity,
    Stage,
)
from acero.epistemic_gate.policy_bridge import check_publication_policy
from acero.epistemic_gate.registry import GateRegistry
from acero.epistemic_gate.rules.inference import artifact_from_gate_input
from acero.inference.audit.gate import GateInput
from acero.policies.guard import PolicyGuard


def test_every_stage_has_rules_except_question():
    reg = GateRegistry()
    for stage in PIPELINE:
        if stage == Stage.QUESTION:
            continue
        assert reg.rule_ids(stage), f"{stage} has no rules"


def test_clean_execution_passes():
    art = {"ran_in_sandbox": True, "secrets_exposed": False, "unauthorized_network": False,
           "environment_recorded": True, "seeds_recorded": True, "hashes_recorded": True,
           "timeout_configured": True, "code_modified_unversioned": False, "reproduced": True}
    res = GlobalGate().check(Stage.EXECUTION, art)
    assert res.outcome == GateOutcome.PASS


def test_execution_blocks_on_sandbox_escape():
    art = {"ran_in_sandbox": False, "secrets_exposed": False, "unauthorized_network": False,
           "environment_recorded": True, "seeds_recorded": True, "hashes_recorded": True,
           "timeout_configured": True, "code_modified_unversioned": False, "reproduced": True}
    res = GlobalGate().check(Stage.EXECUTION, art)
    assert res.outcome == GateOutcome.BLOCKED
    assert any(b.rule_id == "ran_in_sandbox" for b in res.blockers)


def test_missing_input_is_a_warning_not_a_silent_pass():
    res = GlobalGate().check(Stage.EXECUTION, {"ran_in_sandbox": True})
    # the rest are unevaluable → warnings, not blockers
    assert res.outcome == GateOutcome.PASS_WITH_WARNINGS
    assert all(not r.evaluable or r.passed for r in res.results)


def test_inference_stage_blocks_adversarial():
    gi = GateInput(dimensions_valid=False, train_test_disjoint=False, reproduced=False,
                   codex_treated_as_evidence=True)
    res = GlobalGate().check(Stage.INFERENCE, artifact_from_gate_input(gi))
    assert res.outcome == GateOutcome.BLOCKED
    rule_ids = {b.rule_id for b in res.blockers}
    assert {"invalid_dimensions", "data_leakage", "not_reproducible",
            "codex_as_evidence"} <= rule_ids


def test_world_model_confidence_one_blocked():
    art = {"updated_by_codex_only": False, "evidence_has_provenance": True,
           "contradiction_ignored": False, "overwrites_history": False,
           "belief_confidence": 1.0, "dependent_counted_as_independent": False,
           "simulation_as_physical_proof": False, "claim_without_limitations": False}
    res = GlobalGate().check(Stage.WORLD_MODEL_UPDATE, art)
    assert any(b.rule_id == "confidence_below_one" for b in res.blockers)


def test_publication_blocks_ai_authorship():
    art = {"ai_listed_as_author": True, "all_citations_verified": True,
           "reproducible": True, "methodology_complete": True,
           "data_or_code_missing_unjustified": False, "ai_use_undeclared": False,
           "novelty_exaggerated": False, "conflict_of_interest_unreviewed": False,
           "discovery_claim_without_human_review": False,
           "human_understands_central_conclusion": True}
    res = GlobalGate().check(Stage.PUBLICATION, art)
    assert any(b.rule_id == "no_ai_authorship" for b in res.blockers)


def test_human_review_blocked_for_learning():
    art = {"comprehension_status": "BLOCKED_FOR_LEARNING",
           "critical_concepts_assessed": True, "active_blocking_misconception": False,
           "human_prediction_present": True, "limitations_reviewed": True,
           "explicit_human_approval": True}
    res = GlobalGate().check(Stage.HUMAN_REVIEW, art)
    assert res.outcome == GateOutcome.BLOCKED_FOR_LEARNING


# --- Codex advisory discipline --------------------------------------------

def test_codex_finding_not_promoted_without_known_rule():
    res = GlobalGate().check(Stage.INFERENCE, artifact_from_gate_input(GateInput()),
                             codex_findings=[{"concern": "vibe", "detail": "feels off"}])
    # advisory only → a warning, never a blocker
    assert not any(b.rule_id == "vibe" for b in res.blockers)
    assert any("codex" in w.rule_id for w in res.warnings)


def test_codex_finding_promoted_when_names_real_rule():
    res = GlobalGate().check(
        Stage.INFERENCE, artifact_from_gate_input(GateInput()),
        codex_findings=[{"rule": "data_leakage", "detail": "found a leak"}])
    assert any(b.rule_id == "data_leakage" for b in res.blockers)
    assert res.outcome == GateOutcome.BLOCKED


# --- registry: promoting a Codex finding into a rule ----------------------

def test_promotion_requires_checker_and_test():
    reg = GateRegistry()
    with pytest.raises(ValueError):
        reg.promote_codex_finding(rule_id="r", stage=Stage.INFERENCE,
                                  description="d", checker=None, has_test=True)
    with pytest.raises(ValueError):
        reg.promote_codex_finding(rule_id="r", stage=Stage.INFERENCE, description="d",
                                  checker=lambda a: None, has_test=False)


def test_promotion_succeeds_with_checker_and_test():
    reg = GateRegistry()
    r = reg.promote_codex_finding(
        rule_id="new_rule", stage=Stage.INFERENCE, description="d",
        checker=lambda a: None if a.get("ok") else "not ok", has_test=True)
    assert r.source == "codex-promoted"
    assert "new_rule" in reg.rule_ids(Stage.INFERENCE)


# --- policy bridge --------------------------------------------------------

def test_policy_violation_surfaces_as_gate_block():
    guard = PolicyGuard()
    res = check_publication_policy(guard, human_reviewed=False)
    assert res.outcome == GateOutcome.BLOCKED
    res_ok = check_publication_policy(guard, human_reviewed=True)
    assert res_ok.outcome == GateOutcome.PASS


# --- pipeline & self-audit ------------------------------------------------

def test_pipeline_stops_at_blocked_stage():
    gi_bad = GateInput(dimensions_valid=False)
    artifacts = {
        Stage.INFERENCE: artifact_from_gate_input(gi_bad),
        Stage.PUBLICATION: {"ai_listed_as_author": False},
    }
    out = GlobalGate().run_pipeline(artifacts)
    assert out["INFERENCE"].outcome == GateOutcome.BLOCKED
    assert "PUBLICATION" not in out          # knowledge does not flow past a block


def test_self_audit_finds_no_structural_gaps():
    rep = rules_audit()
    assert not any(f.severity == "high" for f in rep.findings)


def test_not_evaluable_exception_type():
    from acero.epistemic_gate.rules.common import must_be_true
    check = must_be_true("k", "detail")
    with pytest.raises(NotEvaluable):
        check({})
    assert check({"k": True}) is None
    assert check({"k": False}) == "detail"


def test_blocker_severity_value():
    assert Severity.BLOCKER.value == "blocker"
