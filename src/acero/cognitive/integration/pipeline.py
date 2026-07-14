"""Integration: fold cognitive results back into the World Model (Sprint 8.5–8.7).

An analogy's validation outcome updates a belief in the World Model: a structurally
supported analogy gains support; a misleading one accrues counter-evidence and a
preserved negative record. This closes the cycle
World Model → Concept → Analogy → First Principles → Evidence → World Model.
"""

from __future__ import annotations

from typing import Any

from ...world_model.edges import EdgeType
from ...world_model.graph import WorldModel
from ...world_model.nodes import NodeType
from ..analogies.models import AnalogyStatus, ScientificAnalogy

_DEEP = {AnalogyStatus.STRUCTURALLY_SUPPORTED, AnalogyStatus.VALID_IN_REGIME}
_BAD = {AnalogyStatus.MISLEADING, AnalogyStatus.BROKEN, AnalogyStatus.REJECTED}


def integrate_analogy(wm: WorldModel, analogy: ScientificAnalogy) -> dict[str, Any]:
    """Create/update a CLAIM belief 'source ~ target (structural)' from the analogy."""
    claim = wm.get_or_create(
        NodeType.CLAIM,
        f"structural analogy: {analogy.source_system} ~ {analogy.target_system}",
        domain=analogy.source_domain,
        data={"subject": f"analogy:{analogy.source_system}~{analogy.target_system}",
              "stance": "holds" if analogy.status in _DEEP else "violated"})
    n_passed = sum(1 for v in analogy.validations if v.passed)
    if analogy.status in _DEEP:
        ev = wm.create(NodeType.EVIDENCE,
                       f"analogy validated ({analogy.status.value}, {n_passed} tests)",
                       domain=analogy.source_domain,
                       data={"deep_score": analogy.scores.deep_score()})
        wm.link(EdgeType.SUPPORTS, ev.id, claim.id, weight=analogy.scores.deep_score(),
                confidence=0.8)
        wm.update_belief(claim.id, event="experiment",
                         evidence=analogy.scores.deep_score(),
                         replication=1 if analogy.status == AnalogyStatus.STRUCTURALLY_SUPPORTED else 0,
                         source=analogy.id)
        outcome = "supported"
    else:
        neg = wm.create(NodeType.NEGATIVE_RESULT,
                        f"misleading analogy: {analogy.source_system} ~ "
                        f"{analogy.target_system}", domain=analogy.source_domain,
                        data={"reason": "surface/geometric similarity without deep structure"})
        wm.link(EdgeType.INVALIDATES, neg.id, claim.id, confidence=0.9)
        wm.update_belief(claim.id, event="experiment", counter=1.0, negative=1,
                         source=analogy.id)
        outcome = "refuted_as_misleading"
    return {"claim_id": claim.id, "outcome": outcome,
            "confidence": wm.get_node(claim.id).confidence}  # type: ignore[union-attr]
