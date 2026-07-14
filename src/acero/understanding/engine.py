"""Human Understanding Engine orchestrator.

Ties the learner model, curriculum, explanations, predictions, assessments, and the
comprehension gate into one service, and folds evidence into knowledge state under the
rules that (a) understanding needs performance evidence, (b) a single answer never grants
mastery, and (c) misconceptions resolve only with new contradicting evidence.

Every research action should produce two parallel updates: a ScientificUpdate (handled by
the science engines) and a HumanUnderstandingUpdate (produced here).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .assessment.grading import build_evidence
from .curriculum.research_curriculum import requirements_for
from .intervention.comprehension_gate import GateContext
from .intervention.comprehension_gate import evaluate as gate_evaluate
from .learner import misconceptions as misc_mod
from .learner.history import LearningEvent, LearningHistory, next_review
from .learner.knowledge_state import (
    apply_evidence,
    mark_misconceived,
    overconfidence_gap,
)
from .models import (
    ComprehensionGateResult,
    EvidenceType,
    KnowledgeState,
    KnowledgeStatus,
    LearnerProfile,
    Misconception,
    ResearchLearningRequirement,
    UnderstandingEvidence,
)
from .store import UnderstandingStore


@dataclass
class HumanUnderstandingUpdate:
    """The learning half of a research cycle (parallel to a ScientificUpdate)."""

    concept: str
    evidence_id: str
    from_status: str
    to_status: str
    misconceptions_detected: list[str] = field(default_factory=list)
    misconceptions_resolved: list[str] = field(default_factory=list)
    overconfidence_gap: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {"concept": self.concept, "evidence_id": self.evidence_id,
                "from": self.from_status, "to": self.to_status,
                "misconceptions_detected": self.misconceptions_detected,
                "misconceptions_resolved": self.misconceptions_resolved,
                "overconfidence_gap": self.overconfidence_gap}


class HumanUnderstandingEngine:
    def __init__(self, store: UnderstandingStore | None = None) -> None:
        self.store = store

    # --- profile --------------------------------------------------------
    def init_learner(self, **kwargs: Any) -> LearnerProfile:
        profile = LearnerProfile(**kwargs)
        if self.store:
            self.store.save_profile(profile)
        return profile

    # --- curriculum -----------------------------------------------------
    def requirements(self, kind: str, project_id: str
                     ) -> list[ResearchLearningRequirement]:
        return requirements_for(kind, project_id)

    # --- assessment → state update -------------------------------------
    def _state(self, learner_id: str, concept_id: str) -> KnowledgeState:
        if self.store:
            st = self.store.load_state(learner_id, concept_id)
            if st:
                return st
        return KnowledgeState(concept_id=concept_id, learner_id=learner_id)

    def _distinct_kinds(self, learner_id: str, concept_id: str) -> set[EvidenceType]:
        if not self.store:
            return set()
        return {e.evidence_type for e in self.store.evidence(learner_id, concept_id)}

    def record_assessment(
        self, learner_id: str, concept_id: str, evidence_type: EvidenceType,
        task: str, response: str, expected_elements: list[str], *,
        confidence: float = 0.5, research_context: str | None = None,
        forbidden_elements: list[str] | None = None,
    ) -> tuple[UnderstandingEvidence, HumanUnderstandingUpdate]:
        """Grade a response, detect misconceptions, and update knowledge state."""
        ev, _grade = build_evidence(
            learner_id, concept_id, evidence_type, task, response, expected_elements,
            confidence=confidence, research_context=research_context,
            forbidden_elements=forbidden_elements)

        prior_kinds = self._distinct_kinds(learner_id, concept_id)
        if self.store:
            self.store.save_evidence(ev)

        state = self._state(learner_id, concept_id)
        outcome = apply_evidence(state, ev, distinct_evidence_kinds=prior_kinds)

        # misconception detection on the response
        detected = misc_mod.detect(response, learner_id=learner_id,
                                   concept_hint=concept_id, source=ev.id)
        detected_ids: list[str] = []
        for m in detected:
            if self.store:
                self.store.save_misconception(m)
            mark_misconceived(state, m.id)
            detected_ids.append(m.id)

        # misconception resolution: passing evidence that no longer triggers the error
        resolved_ids: list[str] = []
        if self.store and ev.score >= 0.7 and not detected:
            for m in self.store.misconceptions(learner_id, open_only=True):
                if misc_mod.resolves(m, ev):
                    m.resolved = True
                    m.resolution_evidence.append(ev.id)
                    self.store.save_misconception(m)
                    if m.id in state.misconceptions:
                        state.misconceptions.remove(m.id)
                    resolved_ids.append(m.id)

        gap = overconfidence_gap(state)
        state.next_review = next_review(state, overconfident=gap > 0.25)
        if self.store:
            self.store.save_state(state)
            self._log(learner_id, LearningEvent(
                "transition", concept_id,
                f"{outcome.from_status.value}->{outcome.to_status.value}",
                research_context_id(research_context),
                payload={"to": outcome.to_status.value, "score": ev.score}))

        update = HumanUnderstandingUpdate(
            concept=concept_id, evidence_id=ev.id,
            from_status=outcome.from_status.value, to_status=state.status.value,
            misconceptions_detected=detected_ids,
            misconceptions_resolved=resolved_ids, overconfidence_gap=gap)
        return ev, update

    def _log(self, learner_id: str, event: LearningEvent) -> None:
        if not self.store:
            return
        events = self.store.history(learner_id)
        h = LearningHistory(learner_id)
        for e in events:
            h.events.append(LearningEvent(**e))
        h.record(event)
        self.store.append_history(learner_id, [e.__dict__ for e in h.events])

    # --- comprehension gate --------------------------------------------
    def comprehension_gate(
        self, learner_id: str, decision: str, required_concepts: list[str], *,
        required_level: KnowledgeStatus | None = None,
        human_override: bool = False, override_reason: str | None = None,
    ) -> ComprehensionGateResult:
        states = {c: self._state(learner_id, c) for c in required_concepts}
        miscs: list[Misconception] = (self.store.misconceptions(learner_id, open_only=True)
                                      if self.store else [])
        ctx = GateContext(decision=decision, required_concepts=required_concepts,
                          states=states, misconceptions=miscs,
                          required_level=required_level)
        result = gate_evaluate(ctx, human_override=human_override,
                               override_reason=override_reason)
        if self.store and result.human_override:
            self._log(learner_id, LearningEvent(
                "override", decision, override_reason or "",
                payload={"blockers": result.blockers}))
        return result

    # --- status ---------------------------------------------------------
    def status(self, learner_id: str) -> dict[str, Any]:
        if not self.store:
            return {"learner_id": learner_id, "states": [], "misconceptions": []}
        states = self.store.states(learner_id)
        miscs = self.store.misconceptions(learner_id)
        return {
            "learner_id": learner_id,
            "n_states": len(states),
            "mastered": [s.concept_id for s in states
                         if s.status == KnowledgeStatus.MASTERED],
            "partial": [s.concept_id for s in states
                        if s.status in (KnowledgeStatus.PARTIALLY_UNDERSTOOD,
                                        KnowledgeStatus.PROCEDURALLY_COMPETENT)],
            "misconceived": [s.concept_id for s in states
                             if s.status == KnowledgeStatus.MISCONCEIVED],
            "open_misconceptions": [m.concept for m in miscs if not m.resolved],
        }


def research_context_id(ctx: str | None) -> str | None:
    return ctx
