"""Sprint 9 property tests for the learner model and the gate."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from acero.epistemic_gate.engine import GlobalGate
from acero.epistemic_gate.models import GateOutcome, Stage
from acero.understanding.assessment.grading import build_evidence
from acero.understanding.learner.knowledge_state import LADDER, apply_evidence
from acero.understanding.models import EvidenceType, KnowledgeState, KnowledgeStatus

_EVIDENCE_TYPES = list(EvidenceType)


@given(
    etype=st.sampled_from(_EVIDENCE_TYPES),
    score=st.floats(min_value=0.0, max_value=1.0),
)
def test_single_evidence_never_reaches_mastered(etype, score):
    """No single piece of evidence, whatever its kind or score, yields MASTERED."""
    st_ = KnowledgeState(concept_id="c", learner_id="lrn")
    ev, _ = build_evidence("lrn", "c", etype, "task", "response", [])
    ev.score = score
    apply_evidence(st_, ev, distinct_evidence_kinds=set())
    assert st_.status != KnowledgeStatus.MASTERED


@given(
    kinds=st.lists(st.sampled_from(_EVIDENCE_TYPES), min_size=1, max_size=8),
)
def test_state_advances_at_most_one_rung_per_evidence(kinds):
    """Each evidence advances the ladder by at most one rung (mastery excepted by count)."""
    state = KnowledgeState(concept_id="c", learner_id="lrn")
    seen: set[EvidenceType] = set()
    for etype in kinds:
        prev = state.status
        ev, _ = build_evidence("lrn", "c", etype, "t", "good imposed library answer",
                               ["good"])
        ev.score = 0.9
        apply_evidence(state, ev, distinct_evidence_kinds=seen)
        seen.add(etype)
        if prev in LADDER and state.status in LADDER:
            # From UNKNOWN the first evidence establishes EXPOSED *and* earns one rung
            # (an initial 2-step exposure jump); after that, at most one rung per evidence.
            max_step = 2 if prev == KnowledgeStatus.UNKNOWN else 1
            assert LADDER.index(state.status) - LADDER.index(prev) <= max_step


@given(
    dims_valid=st.booleans(),
    reproduced=st.booleans(),
    codex_evidence=st.booleans(),
)
def test_inference_gate_blocks_iff_a_blocker_is_present(dims_valid, reproduced,
                                                        codex_evidence):
    artifact = {
        "dimensions_valid": dims_valid,
        "train_test_disjoint": True,
        "derivatives_reliable_or_declared": True,
        "identifiable_or_not_unique": True,
        "equivalent_counted_as_new": False,
        "extrapolation_tested": True,
        "coefficients_have_uncertainty_or_no_precision_claim": True,
        "causal_claim_supported": True,
        "imposed_structure_declared": True,
        "negatives_preserved": True,
        "codex_treated_as_evidence": codex_evidence,
        "confidence_calibrated_or_labeled": True,
        "has_provenance": True,
        "reproduced": reproduced,
        "inference_level": "governing_equation_discovery",
    }
    res = GlobalGate().check(Stage.INFERENCE, artifact)
    has_flaw = (not dims_valid) or (not reproduced) or codex_evidence
    assert (res.outcome == GateOutcome.BLOCKED) == has_flaw
