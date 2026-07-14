"""Sprint 9 tests: comprehension gate, engine orchestration, socratic, pedagogy audit."""

from __future__ import annotations

import pytest

from acero.understanding.audit.engine import rules_audit
from acero.understanding.engine import HumanUnderstandingEngine
from acero.understanding.intervention.comprehension_gate import GateContext, evaluate
from acero.understanding.intervention.socratic import (
    ProjectEntities,
    SocraticKind,
    default_questions,
    filter_codex_questions,
    validate,
)
from acero.understanding.models import (
    ComprehensionStatus,
    Criticality,
    EvidenceType,
    ExplanationArtifact,
    ExplanationLevel,
    KnowledgeState,
    KnowledgeStatus,
    Misconception,
)
from acero.understanding.store import UnderstandingStore

LEARNER = "lrn_g"


def _state(concept, status):
    return KnowledgeState(concept_id=concept, learner_id=LEARNER, status=status)


# --- comprehension gate ---------------------------------------------------

def test_gate_pass_when_concepts_understood():
    ctx = GateContext("update_core_belief", ["c"],
                      {"c": _state("c", KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD)}, [])
    assert evaluate(ctx).status in (ComprehensionStatus.PASS,
                                    ComprehensionStatus.PASS_WITH_SUPPORT)


def test_gate_blocks_for_learning_when_below_level():
    ctx = GateContext("claim_novelty", ["c"],
                      {"c": _state("c", KnowledgeStatus.PARTIALLY_UNDERSTOOD)}, [])
    res = evaluate(ctx)
    assert res.status == ComprehensionStatus.BLOCKED_FOR_LEARNING
    assert res.blockers


def test_gate_blocks_on_active_blocking_misconception():
    m = Misconception(learner_id=LEARNER, concept="c",
                      statement="fit is a law", detected_from="x",
                      severity=Criticality.BLOCKING)
    ctx = GateContext("update_core_belief", ["c"],
                      {"c": _state("c", KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD)}, [m])
    assert evaluate(ctx).status == ComprehensionStatus.BLOCKED_FOR_LEARNING


def test_low_risk_decision_never_blocked():
    ctx = GateContext("view_result", ["c"],
                      {"c": _state("c", KnowledgeStatus.UNKNOWN)}, [])
    assert evaluate(ctx).status == ComprehensionStatus.PASS


def test_override_requires_reason_and_is_recorded():
    ctx = GateContext("publish", ["c"],
                      {"c": _state("c", KnowledgeStatus.UNKNOWN)}, [])
    with pytest.raises(ValueError):
        evaluate(ctx, human_override=True, override_reason="")
    res = evaluate(ctx, human_override=True, override_reason="PI accepts risk")
    assert res.status == ComprehensionStatus.HUMAN_OVERRIDE
    assert res.override_reason == "PI accepts risk"
    assert res.blockers          # blockers are still recorded under override


# --- engine orchestration -------------------------------------------------

def test_engine_records_assessment_and_updates_state(disc_store):
    eng = HumanUnderstandingEngine(UnderstandingStore(disc_store))
    ev, update = eng.record_assessment(
        LEARNER, "imposed_library", EvidenceType.EXPLAIN_OWN_WORDS,
        "why is it not a law?",
        "the term came from an imposed library, selected by fit, not a discovered law",
        ["imposed library", "fit", "law"])
    assert ev.score >= 0.7
    assert update.to_status != "UNKNOWN"
    # persisted
    assert eng.store.load_state(LEARNER, "imposed_library") is not None


def test_engine_detects_misconception_and_marks_state(disc_store):
    eng = HumanUnderstandingEngine(UnderstandingStore(disc_store))
    _, update = eng.record_assessment(
        LEARNER, "governing_structure", EvidenceType.EXPLAIN_OWN_WORDS,
        "what did we find?",
        "we recovered the equation from data so it is a law we discovered",
        ["imposed library"])
    assert update.misconceptions_detected
    assert update.to_status == KnowledgeStatus.MISCONCEIVED.value


def test_engine_comprehension_gate_blocks(disc_store):
    eng = HumanUnderstandingEngine(UnderstandingStore(disc_store))
    res = eng.comprehension_gate(LEARNER, "claim_novelty", ["imposed_library"])
    assert res.status == ComprehensionStatus.BLOCKED_FOR_LEARNING


# --- socratic -------------------------------------------------------------

def test_socratic_questions_reference_real_entities():
    ent = ProjectEntities(concepts=["identifiability"], variables=["x"],
                          equations=["dv/dt = -4x"], code=["engine.py"],
                          results=["damped fit"])
    qs = default_questions(ent)
    assert qs
    assert all(validate(q, ent) for q in qs)


def test_socratic_filters_ungrounded_codex_questions():
    ent = ProjectEntities(concepts=["identifiability"], variables=["x"],
                          equations=[], code=[], results=[])
    cands = [
        {"kind": "evidence", "text": "What identifiability limit applies to x?",
         "references": ["identifiability"]},
        {"kind": "clarification", "text": "What is your favourite colour?",
         "references": []},
    ]
    kept = filter_codex_questions(cands, ent)
    assert len(kept) == 1
    assert kept[0].kind == SocraticKind.EVIDENCE


# --- pedagogy audit -------------------------------------------------------

def test_audit_flags_mastery_from_thin_evidence():
    st = _state("c", KnowledgeStatus.MASTERED)
    rep = rules_audit(states=[st], evidence=[])
    assert any(f.concern == "mastery_from_thin_evidence" for f in rep.findings)


def test_audit_flags_explanation_without_limitations():
    ex = ExplanationArtifact(subject="x", level=ExplanationLevel.INTUITION,
                             limitations=[])
    rep = rules_audit(explanations=[ex])
    assert any(f.concern == "explanation_without_limitations" for f in rep.findings)


def test_audit_clean_when_well_formed():
    st = _state("identifiability", KnowledgeStatus.PARTIALLY_UNDERSTOOD)
    ex = ExplanationArtifact(subject="x", level=ExplanationLevel.INTUITION,
                             limitations=["polynomial library"])
    rep = rules_audit(states=[st], explanations=[ex])
    assert not any(f.severity == "high" for f in rep.findings)


# --- adversarial-audit regression fixes (Sprint 9) ------------------------

def test_keyword_echo_does_not_score_full_pass():
    """Codex-audit fix: a response that merely echoes the rubric keywords is penalised."""
    from acero.understanding.assessment.grading import grade

    echo = grade("imposed library fit", ["imposed", "library", "fit"])
    assert "keyword_echo_without_explanation" in echo.red_flags
    assert echo.score < 0.7

    explained = grade(
        "the term came from the imposed library and was selected only by its fit to data",
        ["imposed", "library", "fit"])
    assert "keyword_echo_without_explanation" not in explained.red_flags
    assert explained.score >= 0.7


def test_status_incoherent_with_ability_flagged():
    """Codex-audit fix: a high status with near-zero measured ability is flagged."""
    st = KnowledgeState(concept_id="c", learner_id="l",
                        status=KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
                        conceptual_understanding=0.0, procedural_ability=0.0)
    rep = rules_audit(states=[st])
    assert any(f.concern == "status_incoherent_with_ability" for f in rep.findings)
