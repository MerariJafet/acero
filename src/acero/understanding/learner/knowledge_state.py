"""The knowledge-state machine.

A concept advances ONLY when there is *evidence of performance*, and each higher state
requires a DIFFERENT kind of evidence than the one below it. A single correct answer
never yields MASTERED. Self-report is recorded but never advances state on its own; if
observed confidence trails self-reported confidence, the gap is surfaced (overconfidence).
"""

from __future__ import annotations

from dataclasses import dataclass

from ...core.clock import now_iso
from ..models import (
    EvidenceType,
    KnowledgeState,
    KnowledgeStatus,
    UnderstandingEvidence,
)

# Ordinal ladder (MISCONCEIVED/DECAYED are off-ladder states handled separately).
LADDER: list[KnowledgeStatus] = [
    KnowledgeStatus.UNKNOWN,
    KnowledgeStatus.EXPOSED,
    KnowledgeStatus.RECOGNIZED,
    KnowledgeStatus.PARTIALLY_UNDERSTOOD,
    KnowledgeStatus.PROCEDURALLY_COMPETENT,
    KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    KnowledgeStatus.TRANSFER_CAPABLE,
    KnowledgeStatus.MASTERED,
]

# Evidence kinds that JUSTIFY reaching each state. Reaching a state needs a passing
# piece of one of its evidence kinds AND the state below already reached.
STATE_EVIDENCE: dict[KnowledgeStatus, set[EvidenceType]] = {
    KnowledgeStatus.RECOGNIZED: {EvidenceType.INTERPRET_GRAPH, EvidenceType.EXPLAIN_OWN_WORDS},
    KnowledgeStatus.PARTIALLY_UNDERSTOOD: {
        EvidenceType.EXPLAIN_OWN_WORDS, EvidenceType.IDENTIFY_ASSUMPTION},
    KnowledgeStatus.PROCEDURALLY_COMPETENT: {
        EvidenceType.SOLVE_SIMILAR, EvidenceType.MODIFY_CODE},
    KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD: {
        EvidenceType.DETECT_ERROR, EvidenceType.COMPARE_MODELS,
        EvidenceType.DERIVE_RESULT, EvidenceType.STATE_LIMITS},
    KnowledgeStatus.TRANSFER_CAPABLE: {EvidenceType.TRANSFER},
    KnowledgeStatus.MASTERED: {EvidenceType.TRANSFER, EvidenceType.PROPOSE_FALSIFICATION},
}

PASS_THRESHOLD = 0.7
# MASTERED additionally requires breadth: distinct evidence kinds already accumulated.
MASTERY_MIN_DISTINCT_EVIDENCE = 4


@dataclass
class TransitionOutcome:
    advanced: bool
    from_status: KnowledgeStatus
    to_status: KnowledgeStatus
    reason: str


def _dim_updates(ev: UnderstandingEvidence) -> dict[str, float]:
    """Map an evidence kind onto the ability dimension it informs."""
    t = ev.evidence_type
    if t in {EvidenceType.SOLVE_SIMILAR, EvidenceType.MODIFY_CODE}:
        return {"procedural_ability": ev.score}
    if t in {EvidenceType.DERIVE_RESULT}:
        return {"mathematical_ability": ev.score}
    if t in {EvidenceType.TRANSFER}:
        return {"transfer_ability": ev.score}
    if t in {EvidenceType.EXPLAIN_OWN_WORDS, EvidenceType.DETECT_ERROR,
             EvidenceType.COMPARE_MODELS, EvidenceType.IDENTIFY_ASSUMPTION,
             EvidenceType.STATE_LIMITS, EvidenceType.PROPOSE_FALSIFICATION}:
        return {"conceptual_understanding": ev.score}
    return {"familiarity": max(ev.score, 0.3)}


def apply_evidence(
    state: KnowledgeState,
    evidence: UnderstandingEvidence,
    *,
    distinct_evidence_kinds: set[EvidenceType] | None = None,
) -> TransitionOutcome:
    """Fold one piece of evidence into the state, advancing at most ONE rung.

    ``distinct_evidence_kinds`` is the set of evidence kinds already recorded for this
    (learner, concept); it gates MASTERED so a single lucky answer can't grant mastery.
    """
    prev = state.status
    state.last_assessed = now_iso()
    state.familiarity = max(state.familiarity, 0.2)
    for k, v in _dim_updates(evidence).items():
        setattr(state, k, max(getattr(state, k), round(v, 4)))
    if evidence.id not in state.evidence:
        state.evidence.append(evidence.id)
    # observed confidence tracks demonstrated ability, not what the learner claims
    state.confidence_observed = round(
        max(state.conceptual_understanding, state.procedural_ability,
            state.mathematical_ability, state.transfer_ability), 4)
    state.confidence_self_reported = max(state.confidence_self_reported, evidence.confidence)

    if evidence.score < PASS_THRESHOLD:
        # exposure only; failing evidence never advances, and may expose a gap
        if prev == KnowledgeStatus.UNKNOWN:
            state.status = KnowledgeStatus.EXPOSED
        return TransitionOutcome(state.status != prev, prev, state.status,
                                 "evidence below pass threshold; no advance")

    kinds = set(distinct_evidence_kinds or set()) | {evidence.evidence_type}
    # From UNKNOWN, any passing evidence reaches at least EXPOSED then the earned rung.
    if prev in (KnowledgeStatus.UNKNOWN, KnowledgeStatus.MISCONCEIVED,
                KnowledgeStatus.DECAYED):
        base_idx = LADDER.index(KnowledgeStatus.EXPOSED)
    else:
        base_idx = LADDER.index(prev)

    target = prev
    for i in range(base_idx + 1, len(LADDER)):
        cand = LADDER[i]
        needed = STATE_EVIDENCE.get(cand, set())
        if needed and not (kinds & needed):
            break
        if cand == KnowledgeStatus.MASTERED and len(kinds) < MASTERY_MIN_DISTINCT_EVIDENCE:
            break
        target = cand
        break  # advance at most one rung per evidence

    if target == prev and prev in (KnowledgeStatus.UNKNOWN,):
        target = KnowledgeStatus.EXPOSED
    state.status = target
    reason = (f"advanced to {target.value} via {evidence.evidence_type.value}"
              if target != prev else "no rung earned by this evidence kind")
    return TransitionOutcome(target != prev, prev, target, reason)


def mark_misconceived(state: KnowledgeState, misconception_id: str) -> None:
    """A detected misconception overrides ladder status until resolved with new evidence."""
    if misconception_id not in state.misconceptions:
        state.misconceptions.append(misconception_id)
    state.status = KnowledgeStatus.MISCONCEIVED
    state.confidence_observed = min(state.confidence_observed, 0.3)


def overconfidence_gap(state: KnowledgeState) -> float:
    """How much self-report exceeds demonstrated ability (0 if calibrated/underconfident)."""
    return round(max(0.0, state.confidence_self_reported - state.confidence_observed), 4)
