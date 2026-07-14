"""The Human Comprehension Gate.

Before a CRITICAL scientific decision, ACERO verifies the human has demonstrated minimum
comprehension of the concepts the decision depends on. Low-risk actions are NOT blocked
(no paternalism). The human may override any block, but the override and its reason are
recorded. Active, unresolved HIGH/BLOCKING misconceptions on a required concept block the
decision until resolved with new evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..learner.knowledge_state import LADDER
from ..models import (
    ComprehensionGateResult,
    ComprehensionStatus,
    Criticality,
    KnowledgeState,
    KnowledgeStatus,
    Misconception,
)

# Decisions that require demonstrated comprehension, with their default required level.
CRITICAL_DECISIONS: dict[str, KnowledgeStatus] = {
    "accept_hypothesis_as_priority": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    "discard_model": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    "approve_expensive_experiment": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    "update_core_belief": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    "claim_novelty": KnowledgeStatus.TRANSFER_CAPABLE,
    "publish": KnowledgeStatus.TRANSFER_CAPABLE,
    "approve_future_physical_experiment": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    "interpret_causal_conclusion": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
    "approve_incomplete_derivation": KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD,
}

# Decisions considered low-risk — never blocked for pedagogy.
LOW_RISK_DECISIONS = {"view_result", "run_local_sim", "read_explanation",
                      "generate_hypotheses", "export_local_draft"}


def _rank(status: KnowledgeStatus) -> int:
    try:
        return LADDER.index(status)
    except ValueError:
        return -1                        # MISCONCEIVED / DECAYED are below EXPOSED


@dataclass
class GateContext:
    decision: str
    required_concepts: list[str]
    states: dict[str, KnowledgeState]           # concept -> state
    misconceptions: list[Misconception]
    required_level: KnowledgeStatus | None = None


def evaluate(ctx: GateContext, *, human_override: bool = False,
             override_reason: str | None = None) -> ComprehensionGateResult:
    """Decide whether the human may proceed with a critical decision."""
    decision = ctx.decision
    if decision in LOW_RISK_DECISIONS:
        return ComprehensionGateResult(
            decision=decision, required_concepts=[],
            status=ComprehensionStatus.PASS,
            required_level=KnowledgeStatus.EXPOSED)

    required_level = (ctx.required_level
                      or CRITICAL_DECISIONS.get(decision)
                      or KnowledgeStatus.CONCEPTUALLY_UNDERSTOOD)
    need = _rank(required_level)
    blockers: list[str] = []

    for concept in ctx.required_concepts:
        st = ctx.states.get(concept)
        if st is None:
            blockers.append(f"{concept}: not assessed")
            continue
        if st.status == KnowledgeStatus.MISCONCEIVED:
            blockers.append(f"{concept}: active misconception (MISCONCEIVED)")
            continue
        if _rank(st.status) < need:
            blockers.append(
                f"{concept}: at {st.status.value}, need {required_level.value}")

    # Unresolved HIGH/BLOCKING misconceptions on a required concept always block.
    for m in ctx.misconceptions:
        if (not m.resolved and m.concept in ctx.required_concepts
                and m.severity in (Criticality.HIGH, Criticality.BLOCKING)):
            msg = f"{m.concept}: unresolved {m.severity.value} misconception '{m.statement}'"
            if msg not in blockers:
                blockers.append(msg)

    misc_ids = [m.id for m in ctx.misconceptions if m.concept in ctx.required_concepts]
    assess_ids = [e for st in ctx.states.values() for e in st.evidence]

    if not blockers:
        # Everything at required level with no blocking misconception → PASS.
        # If some concept is only just at level (borderline), offer support.
        borderline = any(_rank(st.status) == need
                         for st in ctx.states.values())
        status = (ComprehensionStatus.PASS_WITH_SUPPORT if borderline
                  else ComprehensionStatus.PASS)
        return ComprehensionGateResult(
            decision=decision, required_concepts=ctx.required_concepts,
            required_level=required_level, assessments=assess_ids,
            misconceptions=misc_ids, status=status)

    if human_override:
        if not override_reason:
            raise ValueError("a human override must record a reason")
        return ComprehensionGateResult(
            decision=decision, required_concepts=ctx.required_concepts,
            required_level=required_level, assessments=assess_ids,
            misconceptions=misc_ids, status=ComprehensionStatus.HUMAN_OVERRIDE,
            blockers=blockers, human_override=True, override_reason=override_reason)

    return ComprehensionGateResult(
        decision=decision, required_concepts=ctx.required_concepts,
        required_level=required_level, assessments=assess_ids,
        misconceptions=misc_ids, status=ComprehensionStatus.BLOCKED_FOR_LEARNING,
        blockers=blockers)
