"""Mandatory epistemic gate tests."""

from __future__ import annotations

from acero.inference.audit.gate import GateInput, GateStatus, evaluate
from acero.inference.models import IdentifiabilityStatus


def test_clean_candidate_passes():
    rep = evaluate(GateInput(inference_level="governing_equation_discovery"))
    assert rep.status == GateStatus.PASS


def test_invalid_dimensions_blocks():
    rep = evaluate(GateInput(dimensions_valid=False))
    assert rep.status == GateStatus.BLOCKED
    assert any(f.rule == "invalid_dimensions" for f in rep.blockers)


def test_leakage_blocks():
    assert evaluate(GateInput(train_test_disjoint=False)).status == GateStatus.BLOCKED


def test_not_reproducible_blocks():
    assert any(f.rule == "not_reproducible"
               for f in evaluate(GateInput(reproduced=False)).blockers)


def test_harking_blocks():
    assert any(f.rule == "harking" for f in evaluate(GateInput(preregistered=False)).blockers)


def test_deleted_negative_blocks():
    assert any(f.rule == "negative_result_deleted"
               for f in evaluate(GateInput(negatives_preserved=False)).blockers)


def test_non_identifiable_presented_as_unique_blocks():
    rep = evaluate(GateInput(identifiability=IdentifiabilityStatus.NON_IDENTIFIABLE,
                             presented_as_unique=True))
    assert any(f.rule == "non_identifiable_presented_as_unique" for f in rep.blockers)


def test_causal_claim_without_evidence_blocks():
    rep = evaluate(GateInput(makes_causal_claim=True, has_intervention_evidence=False))
    assert any(f.rule == "causal_claim_without_evidence" for f in rep.blockers)


def test_causal_claim_with_evidence_ok():
    rep = evaluate(GateInput(makes_causal_claim=True, has_intervention_evidence=True,
                             inference_level="causal_discovery"))
    assert rep.status != GateStatus.BLOCKED


def test_equivalent_counted_as_new_blocks():
    rep = evaluate(GateInput(n_equivalent_models=3, counts_equivalent_as_new=True))
    assert any(f.rule == "equivalent_counted_as_new" for f in rep.blockers)


def test_codex_as_evidence_blocks():
    assert any(f.rule == "codex_as_evidence"
               for f in evaluate(GateInput(codex_treated_as_evidence=True)).blockers)


def test_extrapolation_without_test_blocks():
    assert any(f.rule == "extrapolation_without_test"
               for f in evaluate(GateInput(extrapolation_tested=False)).blockers)


def test_undeclared_miscalibration_blocks():
    rep = evaluate(GateInput(known_miscalibrated=True, calibration_declared=False))
    assert any(f.rule == "undeclared_miscalibration" for f in rep.blockers)


def test_data_insufficient_escalates():
    rep = evaluate(GateInput(identifiability=IdentifiabilityStatus.DATA_INSUFFICIENT))
    assert rep.status == GateStatus.ESCALATE_TO_HUMAN


def test_level_overstatement_is_warning():
    rep = evaluate(GateInput(inference_level="curve_fitting"))
    assert rep.status == GateStatus.PASS_WITH_WARNINGS


def test_codex_finding_only_promoted_when_matches_rule():
    # A Codex finding naming a known rule becomes a blocker.
    rep = evaluate(GateInput(),
                   codex_findings=[{"rule": "data_leakage", "detail": "hidden split"}])
    assert rep.status == GateStatus.BLOCKED
    # An arbitrary Codex concern is only a warning.
    rep2 = evaluate(GateInput(),
                    codex_findings=[{"concern": "vibes", "detail": "seems off"}])
    assert rep2.status != GateStatus.BLOCKED
