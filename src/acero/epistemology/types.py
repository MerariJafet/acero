"""The epistemic type system: the kinds of scientific objects ACERO represents."""

from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    OBSERVATION = "OBSERVATION"
    MEASUREMENT = "MEASUREMENT"
    DATASET = "DATASET"
    CLAIM = "CLAIM"
    EVIDENCE = "EVIDENCE"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    ASSUMPTION = "ASSUMPTION"
    QUESTION = "QUESTION"
    HYPOTHESIS = "HYPOTHESIS"
    PREDICTION = "PREDICTION"
    MODEL = "MODEL"
    METHOD = "METHOD"
    EXPERIMENT = "EXPERIMENT"
    RESULT = "RESULT"
    NEGATIVE_RESULT = "NEGATIVE_RESULT"
    ANOMALY = "ANOMALY"
    CONTRADICTION = "CONTRADICTION"
    INFERENCE = "INFERENCE"
    CONCLUSION = "CONCLUSION"
    LIMITATION = "LIMITATION"
    OPEN_QUESTION = "OPEN_QUESTION"
    RETRACTION = "RETRACTION"
    CORRECTION = "CORRECTION"


class EntityState(str, Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    TESTED = "TESTED"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    REFUTED = "REFUTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    ARCHIVED = "ARCHIVED"


# Allowed state transitions. Illegal jumps are rejected by the ledger service.
STATE_TRANSITIONS: dict[EntityState, set[EntityState]] = {
    EntityState.DRAFT: {EntityState.PROPOSED, EntityState.ARCHIVED},
    EntityState.PROPOSED: {EntityState.APPROVED, EntityState.ARCHIVED, EntityState.DRAFT},
    EntityState.APPROVED: {EntityState.ACTIVE, EntityState.ARCHIVED},
    EntityState.ACTIVE: {EntityState.TESTED, EntityState.ARCHIVED},
    EntityState.TESTED: {
        EntityState.SUPPORTED,
        EntityState.WEAKENED,
        EntityState.REFUTED,
        EntityState.INCONCLUSIVE,
        EntityState.ARCHIVED,
    },
    EntityState.SUPPORTED: {EntityState.WEAKENED, EntityState.REFUTED, EntityState.ARCHIVED},
    EntityState.WEAKENED: {EntityState.REFUTED, EntityState.SUPPORTED, EntityState.ARCHIVED},
    EntityState.REFUTED: {EntityState.ARCHIVED},
    EntityState.INCONCLUSIVE: {
        EntityState.TESTED,
        EntityState.SUPPORTED,
        EntityState.WEAKENED,
        EntityState.REFUTED,
        EntityState.ARCHIVED,
    },
    EntityState.ARCHIVED: set(),
}


def can_transition(src: EntityState, dst: EntityState) -> bool:
    return dst in STATE_TRANSITIONS.get(src, set())
