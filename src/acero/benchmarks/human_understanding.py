"""Human-in-the-Loop Scientific Understanding Benchmark.

Uses REAL ACERO investigations (SINDy inference, the oscillator↔RLC analogy, the SILSO
sunspot analysis, an adversarial report) to test that the Human Understanding Engine
measures understanding by performance, catches misconceptions, requires predictions, and
that the Global Epistemic Gate blocks a flawed report. It also runs a cross-domain
transfer case (identifiability: oscillator → logistic growth).

This validates the METHOD; it is not a claim about any specific human.
"""

from __future__ import annotations

from typing import Any

from ..epistemic_gate.engine import GlobalGate
from ..epistemic_gate.models import GateOutcome, Stage
from ..epistemic_gate.rules.inference import artifact_from_gate_input
from ..inference.audit.gate import GateInput
from ..understanding.assessment.grading import build_evidence
from ..understanding.assessment.predictions import (
    is_overconfident,
    make_prediction,
    reveal,
)
from ..understanding.assessment.transfer import assess_transfer
from ..understanding.curriculum.research_curriculum import requirements_for
from ..understanding.intervention.comprehension_gate import GateContext, evaluate
from ..understanding.learner import misconceptions as misc_mod
from ..understanding.learner.knowledge_state import apply_evidence
from ..understanding.models import (
    ComprehensionStatus,
    EvidenceType,
    KnowledgeState,
    KnowledgeStatus,
)

LEARNER = "lrn_benchmark"


def _accumulate(concept: str, items: list[tuple[EvidenceType, str, str, list[str]]]
                ) -> KnowledgeState:
    """Drive a concept's state through several DISTINCT evidence kinds."""
    state = KnowledgeState(concept_id=concept, learner_id=LEARNER)
    kinds: set[EvidenceType] = set()
    for etype, task, response, expected in items:
        ev, _ = build_evidence(LEARNER, concept, etype, task, response, expected)
        apply_evidence(state, ev, distinct_evidence_kinds=kinds)
        kinds.add(etype)
    return state


def case_sindy() -> dict[str, Any]:
    """The human must distinguish fit from structure and catch the 'law' misconception."""
    requirements_for("sindy", "proj_sindy")     # research-derived requirements exist
    # A correct explanation of the imposed library → conceptual understanding.
    good = _accumulate("imposed_library", [
        (EvidenceType.EXPLAIN_OWN_WORDS, "Why isn't ẋ=-0.7x a discovered law?",
         "the term x came from a library we imposed; STLSQ selected it by fit, so this is "
         "system identification, not a discovered law",
         ["imposed library", "fit not law", "system identification"]),
        (EvidenceType.MODIFY_CODE, "Change the library to test sensitivity.",
         "I added and removed candidate terms and re-ran STLSQ to see which survive",
         ["added", "removed", "terms", "re-ran"]),
        (EvidenceType.DETECT_ERROR, "Spot the error: 'best fit ⇒ true mechanism'.",
         "that conflates fit with mechanism; equal-fitting models can differ",
         ["conflates fit", "equal fitting models"]),
        (EvidenceType.COMPARE_MODELS, "Compare two equal-RMSE models.",
         "same fit, different mechanism, so RMSE cannot decide the mechanism",
         ["same fit", "different mechanism"]),
    ])
    # A wrong belief triggers the misconception detector.
    misread = ("we recovered the equation from data so it is a law we discovered")
    detected = misc_mod.detect(misread, learner_id=LEARNER)

    # Comprehension gate for a novelty claim requires TRANSFER_CAPABLE — good is only
    # conceptual, so the claim is blocked for learning.
    ctx = GateContext(decision="claim_novelty", required_concepts=["imposed_library"],
                      states={"imposed_library": good}, misconceptions=[],
                      required_level=KnowledgeStatus.TRANSFER_CAPABLE)
    gate = evaluate(ctx)
    return {
        "concept_status": good.status.value,
        "misconception_detected": [m.statement for m in detected],
        "novelty_gate": gate.status.value,
        "novelty_blocked": gate.status == ComprehensionStatus.BLOCKED_FOR_LEARNING,
    }


def case_analogy() -> dict[str, Any]:
    """Oscillator↔RLC: map variables, know what's conserved, reject full equivalence."""
    state = _accumulate("analogy_structure", [
        (EvidenceType.EXPLAIN_OWN_WORDS, "Map the oscillator to the RLC circuit.",
         "position→charge, velocity→current, mass→inductance, spring→1/capacitance; the "
         "ODE form is the same, not the physics",
         ["charge", "current", "inductance", "same ode", "not the physics"]),
        (EvidenceType.SOLVE_SIMILAR, "Solve for the resonant frequency of the RLC analogue.",
         "using the mapping, ω=1/sqrt(LC), the same form as sqrt(k/m)",
         ["1/sqrt(lc)", "same form"]),
        (EvidenceType.STATE_LIMITS, "Where does the analogy break?",
         "it breaks under nonlinearity and saturation; it is valid in the linear regime",
         ["nonlinearity", "linear regime"]),
    ])
    # Reject full physical equivalence — a correct 'analogy≠equivalence' answer.
    resp = "an analogy is structural, it does not mean the systems are physically identical"
    wrong = misc_mod.detect(resp, learner_id=LEARNER)   # should be empty (correct)
    # Transfer a prediction (resonance) — TRANSFER evidence.
    return {
        "concept_status": state.status.value,
        "false_equivalence_flagged": bool(wrong),       # expected False
        "rejects_equivalence": not wrong,
    }


def case_sunspots() -> dict[str, Any]:
    """Distinguish periodicity from mechanism; 11.2yr does not prove the dynamo."""
    state = _accumulate("mechanism_vs_pattern", [
        (EvidenceType.EXPLAIN_OWN_WORDS, "Does an 11.2yr period prove the solar dynamo?",
         "no; a period is a pattern in the data and does not demonstrate the dynamo "
         "mechanism; the series is quasiperiodic with gaps",
         ["period is a pattern", "does not demonstrate", "quasiperiodic"]),
        (EvidenceType.INTERPRET_GRAPH, "Read the FFT: what does the dominant peak mean?",
         "the dominant peak marks the ~11.2 year cycle length, a pattern not a mechanism",
         ["dominant peak", "cycle length", "pattern"]),
        (EvidenceType.SOLVE_SIMILAR, "Estimate the period from two successive maxima.",
         "the spacing between maxima is about 11 years, matching the FFT",
         ["spacing", "11 years"]),
        (EvidenceType.STATE_LIMITS, "What can't be concluded from the sunspot series?",
         "we cannot infer the mechanism or predict future cycles from this series alone",
         ["cannot infer the mechanism", "series alone"]),
    ])
    bad = "the 11.2 year period proves the dynamo mechanism"
    detected = misc_mod.detect(bad, learner_id=LEARNER)
    return {
        "concept_status": state.status.value,
        "misconception_on_bad_claim": [m.concept for m in detected],
        "distinguishes_pattern_mechanism": state.status in (
            KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD, KnowledgeStatus.PARTIALLY_UNDERSTOOD),
    }


def case_adversarial_gate() -> dict[str, Any]:
    """A flawed report must be BLOCKED by the global gate; the human must detect why."""
    gi = GateInput(
        train_test_disjoint=False,           # leakage
        known_miscalibrated=True, calibration_declared=False,   # miscalibration hidden
        makes_causal_claim=True, has_intervention_evidence=False,  # causal w/o evidence
        reproduced=False,                    # not reproducible
        codex_treated_as_evidence=True)      # Codex-as-evidence
    result = GlobalGate().check(Stage.INFERENCE, artifact_from_gate_input(gi))

    # The human demonstrates they can DETECT the flaws (detect_error evidence).
    human = build_evidence(
        LEARNER, "epistemics", EvidenceType.DETECT_ERROR,
        "List the problems in this report.",
        "there is train/test leakage, hidden miscalibration, a causal claim without "
        "intervention evidence, it is not reproducible, and Codex is used as evidence",
        ["leakage", "miscalibration", "causal", "reproducible", "codex"])[1]
    return {
        "gate_outcome": result.outcome.value,
        "gate_blocked": result.outcome == GateOutcome.BLOCKED,
        "n_blockers": len(result.blockers),
        "blocker_rules": sorted(b.rule_id for b in result.blockers),
        "human_detected_score": human.score,
    }


def case_transfer() -> dict[str, Any]:
    """Learn identifiability on the oscillator, apply it to logistic growth (unseen)."""
    ev, grade = assess_transfer(
        LEARNER, "identifiability",
        "No — if the data never approaches the carrying capacity, K is not identifiable; "
        "the data does not constrain it, so many K values fit equally well.",
        confidence=0.7, research_context="proj_transfer")
    # A weak/wrong transfer answer for contrast.
    _, weak = assess_transfer(
        LEARNER, "identifiability",
        "K is uniquely determined by the fit.", confidence=0.9)
    return {
        "transfer_score": ev.score,
        "transfer_pass": ev.score >= 0.7,
        "wrong_answer_score": weak.score,
        "wrong_answer_flagged": weak.red_flags,
    }


def case_prediction() -> dict[str, Any]:
    """Prediction-before-result: lock, compare, detect overconfidence."""
    p = make_prediction(LEARNER, "proj_sindy", "exp_noise",
                        "R² will stay near 1.0 even at high noise", confidence=0.85)
    reveal(p, "R² dropped to 0.29 at noise 0.1", correct_tokens=["0.29", "dropped"])
    return {
        "comparison": p.comparison,
        "locked": p.locked,
        "overconfident": is_overconfident(p),
    }


def run_human_understanding() -> dict[str, Any]:
    """Run the full benchmark and return a structured report."""
    return {
        "case_1_sindy": case_sindy(),
        "case_2_analogy": case_analogy(),
        "case_3_sunspots": case_sunspots(),
        "case_4_adversarial_gate": case_adversarial_gate(),
        "transfer": case_transfer(),
        "prediction": case_prediction(),
    }
