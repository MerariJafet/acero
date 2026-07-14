"""Typed epistemic relations (edges). Each edge is itself weighted and dated."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..core.clock import now_iso
from ..core.ids import new_id


class EdgeType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    GENERATED_BY = "generated_by"
    TESTS = "tests"
    EXPLAINS = "explains"
    PREDICTS = "predicts"
    DERIVED_FROM = "derived_from"
    REFINES = "refines"
    GENERALIZES = "generalizes"
    SPECIALIZES = "specializes"
    INVALIDATES = "invalidates"
    REQUIRES = "requires"
    BELONGS_TO = "belongs_to"
    MEASURED_BY = "measured_by"
    COMPUTED_BY = "computed_by"
    OBSERVED_IN = "observed_in"
    RELATED_TO = "related_to"
    CAUSED_BY = "caused_by"
    HYPOTHESIZES = "hypothesizes"
    EXTENDS = "extends"
    REPLACES = "replaces"


# Edges that push support up/down on their target belief.
POSITIVE_EDGES = {EdgeType.SUPPORTS, EdgeType.EXPLAINS, EdgeType.PREDICTS}
NEGATIVE_EDGES = {EdgeType.CONTRADICTS, EdgeType.INVALIDATES}


class WorldEdge(BaseModel):
    id: str = Field(default_factory=lambda: new_id("we"))
    project_id: str
    type: EdgeType
    source: str  # node id
    target: str  # node id
    weight: float = 1.0          # relation strength (mutable over time)
    confidence: float = 0.5      # confidence IN the relation itself
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    active: bool = True          # weakened relations are deactivated, not deleted
    data: dict[str, Any] = Field(default_factory=dict)


def make_edge(project_id: str, etype: EdgeType, source: str, target: str,
              *, weight: float = 1.0, confidence: float = 0.5, **kw: Any) -> WorldEdge:
    return WorldEdge(project_id=project_id, type=etype, source=source, target=target,
                     weight=weight, confidence=confidence, **kw)
