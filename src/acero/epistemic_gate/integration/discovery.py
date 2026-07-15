"""Gate-guarded Discovery Store.

Wraps `DiscoveryStore` so promoting a hypothesis, approving a design, or closing a result
goes through the inline gate first. A blocked write performs NO mutation.
"""

from __future__ import annotations

from typing import Any

from ...discovery.store import DiscoveryStore
from ..enforcement import GateEnforcer, Override
from ..models import Stage


class GuardedDiscoveryStore:
    def __init__(self, store: DiscoveryStore, enforcer: GateEnforcer | None = None) -> None:
        self.store = store
        self._enforcer = enforcer or GateEnforcer()

    def __getattr__(self, item: str) -> Any:      # pragma: no cover - read passthrough
        return getattr(self.store, item)

    def promote(self, project_id: str, kind: str, obj_id: str, payload: dict[str, Any],
                *, stage: Stage, artifact: dict[str, Any], status: str = "PROMOTED",
                override: Override | None = None, actor: str = "system") -> Any:
        """Promote/accept a discovery object only if the stage gate passes."""
        gpa, _ = self._enforcer.enforce(
            action=f"discovery.promote.{kind}", stage=stage, artifact=artifact,
            mutation=lambda: self.store.put(project_id, kind, obj_id, payload,
                                            status=status, actor=actor),
            context={"actor": actor}, override=override,
            artifact_ids=(obj_id,), project_id=project_id)
        return gpa

    def close_result(self, obj_id: str, *, project_id: str, artifact: dict[str, Any],
                     status: str = "CLOSED", override: Override | None = None,
                     actor: str = "system") -> Any:
        gpa, _ = self._enforcer.enforce(
            action="discovery.close_result", stage=Stage.EXECUTION, artifact=artifact,
            mutation=lambda: self.store.set_status(obj_id, status, actor=actor),
            context={"actor": actor}, override=override,
            artifact_ids=(obj_id,), project_id=project_id)
        return gpa

    @property
    def metrics(self) -> Any:
        return self._enforcer.metrics
