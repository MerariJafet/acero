"""Conceptual dependency ontology: how concepts relate and which relations must be acyclic."""

from __future__ import annotations

from ...world_model.edges import EdgeType

# Conceptual dependency name -> World Model edge type.
DEPENDENCY_EDGE: dict[str, EdgeType] = {
    "requires": EdgeType.REQUIRES,
    "presupposes": EdgeType.PRESUPPOSES,
    "derived_from": EdgeType.DERIVED_FROM,
    "generalizes": EdgeType.GENERALIZES,
    "specializes": EdgeType.SPECIALIZES,
    "emerges_from": EdgeType.EMERGES_FROM,
    "approximates": EdgeType.APPROXIMATES,
    "replaces": EdgeType.REPLACES,
    "breaks_down_when": EdgeType.BREAKS_DOWN_WHEN,
    "is_dual_to": EdgeType.IS_DUAL_TO,
    "is_invariant_under": EdgeType.IS_INVARIANT_UNDER,
    "depends_on": EdgeType.DEPENDS_ON,
}

# Relations that must NOT form cycles (a concept cannot ultimately require itself).
ACYCLIC = {"requires", "presupposes", "derived_from", "depends_on", "emerges_from"}
