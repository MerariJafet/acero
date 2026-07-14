"""Persistence for the Human Understanding Engine.

Reuses the generic ``discovery`` table via DiscoveryStore (no new migration): the learner
profile, knowledge states, misconceptions, evidence, predictions and history are stored
as payloads keyed by kind. Learner-global objects live under a fixed pseudo-project id so
they persist independently of any single research project.
"""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from ..provenance.events import ProvenanceAction
from .models import (
    HumanPrediction,
    KnowledgeState,
    LearnerProfile,
    Misconception,
    UnderstandingEvidence,
)

LEARNER_SCOPE = "_learner"          # pseudo-project id for learner-global objects


class UnderstandingStore:
    def __init__(self, store: DiscoveryStore) -> None:
        self._store = store

    # --- profile --------------------------------------------------------
    def save_profile(self, profile: LearnerProfile) -> None:
        self._store.put(LEARNER_SCOPE, "learner_profile", profile.learner_id,
                        profile.model_dump(), status="ACTIVE",
                        summary="learner profile saved")

    def load_profile(self, learner_id: str) -> LearnerProfile | None:
        raw = self._store.get(learner_id)
        return LearnerProfile(**raw) if raw else None

    def profiles(self) -> list[LearnerProfile]:
        return [LearnerProfile(**r)
                for r in self._store.list_objects(LEARNER_SCOPE, kind="learner_profile")]

    # --- knowledge state ------------------------------------------------
    def _ks_id(self, learner_id: str, concept_id: str) -> str:
        return f"ks_{learner_id}_{concept_id}"

    def save_state(self, state: KnowledgeState) -> None:
        self._store.put(LEARNER_SCOPE, "knowledge_state",
                        self._ks_id(state.learner_id, state.concept_id),
                        state.model_dump(), status=state.status.value,
                        action=ProvenanceAction.UPDATE,
                        summary=f"{state.concept_id} -> {state.status.value}")

    def load_state(self, learner_id: str, concept_id: str) -> KnowledgeState | None:
        raw = self._store.get(self._ks_id(learner_id, concept_id))
        return KnowledgeState(**raw) if raw else None

    def states(self, learner_id: str) -> list[KnowledgeState]:
        return [KnowledgeState(**r)
                for r in self._store.list_objects(LEARNER_SCOPE, kind="knowledge_state")
                if r.get("learner_id") == learner_id]

    # --- misconceptions -------------------------------------------------
    def save_misconception(self, m: Misconception) -> None:
        self._store.put(LEARNER_SCOPE, "misconception", m.id, m.model_dump(),
                        status="RESOLVED" if m.resolved else "OPEN",
                        summary=f"misconception[{m.concept}] resolved={m.resolved}")

    def misconceptions(self, learner_id: str, *, open_only: bool = False
                       ) -> list[Misconception]:
        out = [Misconception(**r)
               for r in self._store.list_objects(LEARNER_SCOPE, kind="misconception")
               if r.get("learner_id") == learner_id]
        return [m for m in out if not m.resolved] if open_only else out

    # --- evidence -------------------------------------------------------
    def save_evidence(self, ev: UnderstandingEvidence) -> None:
        self._store.put(LEARNER_SCOPE, "understanding_evidence", ev.id,
                        ev.model_dump(), status="RECORDED",
                        summary=f"evidence[{ev.evidence_type.value}] score={ev.score}")

    def evidence(self, learner_id: str, concept_id: str | None = None
                 ) -> list[UnderstandingEvidence]:
        out = [UnderstandingEvidence(**r)
               for r in self._store.list_objects(LEARNER_SCOPE,
                                                  kind="understanding_evidence")
               if r.get("learner_id") == learner_id]
        return [e for e in out if concept_id is None or e.concept_id == concept_id]

    # --- predictions ----------------------------------------------------
    def save_prediction(self, p: HumanPrediction) -> None:
        self._store.put(LEARNER_SCOPE, "human_prediction", p.id, p.model_dump(),
                        status="LOCKED" if p.locked else "OPEN",
                        action=ProvenanceAction.UPDATE,
                        summary=f"prediction {p.comparison or 'pending'}")

    def predictions(self, learner_id: str) -> list[HumanPrediction]:
        return [HumanPrediction(**r)
                for r in self._store.list_objects(LEARNER_SCOPE, kind="human_prediction")
                if r.get("learner_id") == learner_id]

    # --- history --------------------------------------------------------
    def append_history(self, learner_id: str, events: list[dict[str, Any]]) -> None:
        self._store.put(LEARNER_SCOPE, "learning_history", f"hist_{learner_id}",
                        {"learner_id": learner_id, "events": events},
                        action=ProvenanceAction.UPDATE, summary="history updated")

    def history(self, learner_id: str) -> list[dict[str, Any]]:
        raw = self._store.get(f"hist_{learner_id}")
        return list(raw.get("events", [])) if raw else []
