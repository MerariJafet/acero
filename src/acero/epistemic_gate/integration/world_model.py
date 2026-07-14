"""Gate-guarded World Model.

Wraps `WorldModel` so belief updates and relation writes go through the inline gate first.
A blocked update performs NO mutation and records a rejection; a raw `WorldModel` write
attempted outside this path raises BypassDetected (because these methods open the only
valid gate context).
"""

from __future__ import annotations

from typing import Any

from ...world_model.graph import WorldModel
from ..enforcement import GateEnforcer, Override
from ..models import Stage


class GatedWorldModel:
    def __init__(self, wm: WorldModel, enforcer: GateEnforcer | None = None) -> None:
        self.wm = wm
        self._enforcer = enforcer or GateEnforcer()

    # read-through
    def __getattr__(self, item: str) -> Any:      # pragma: no cover - passthrough
        return getattr(self.wm, item)

    def update_belief_gated(
        self, node_id: str, *, artifact: dict[str, Any], event: str,
        evidence: float = 0.0, override: Override | None = None,
        actor: str = "system", **kw: Any) -> Any:
        """Accept/update a belief only if the WORLD_MODEL_UPDATE gate passes."""
        gpa, node = self._enforcer.enforce(
            action="world_model.update_belief", stage=Stage.WORLD_MODEL_UPDATE,
            artifact=artifact,
            mutation=lambda: self.wm.update_belief(
                node_id, event=event, evidence=evidence, actor=actor, **kw),
            context={"actor": actor, "node_id": node_id}, override=override)
        return gpa, node

    def link_gated(self, etype: Any, source: str, target: str, *,
                   artifact: dict[str, Any], override: Override | None = None,
                   actor: str = "system", **kw: Any) -> Any:
        """Add a relation only if the WORLD_MODEL_UPDATE gate passes."""
        gpa, edge = self._enforcer.enforce(
            action="world_model.link", stage=Stage.WORLD_MODEL_UPDATE, artifact=artifact,
            mutation=lambda: self.wm.link(etype, source, target, actor=actor, **kw),
            context={"actor": actor}, override=override)
        return gpa, edge

    @property
    def metrics(self) -> Any:
        return self._enforcer.metrics

    @property
    def trace(self) -> Any:
        return self._enforcer.trace
