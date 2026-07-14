"""Negative Results Registry (Sprint 7.7).

Preserves failed hypotheses, failing configurations, errors, null results,
inconclusive attempts, and tools that did not work — with the reason. Queryable
BEFORE repeating an experiment so the engine does not waste compute re-failing.
Records are never deleted (enforced by DiscoveryStore).
"""

from __future__ import annotations

from typing import Any

from ..core.hashing import hash_json
from ..core.ids import new_id
from ..provenance.events import ProvenanceAction
from .store import DiscoveryStore


def config_signature(config: dict[str, Any]) -> str:
    return hash_json(config)


class NegativeResultsRegistry:
    def __init__(self, store: DiscoveryStore, project_id: str) -> None:
        self.store = store
        self.project_id = project_id

    def record(self, *, kind: str, summary: str, config: dict[str, Any] | None = None,
               hypothesis_id: str | None = None, error: str = "",
               reason: str = "") -> dict[str, Any]:
        """kind: failed_hypothesis | null_result | inconclusive | error | tool_failed."""
        rec_id = new_id("neg")
        sig = config_signature(config or {})
        payload = {
            "id": rec_id, "negative_kind": kind, "summary": summary,
            "config": config or {}, "config_signature": sig,
            "hypothesis_id": hypothesis_id, "error": error, "reason": reason,
        }
        self.store.put(
            self.project_id, "negative", rec_id, payload, status="RECORDED",
            action=ProvenanceAction.CREATE, summary=f"negative[{kind}]: {summary}",
        )
        return payload

    def all(self) -> list[dict[str, Any]]:
        return self.store.list_objects(self.project_id, kind="negative")

    def already_tried(self, config: dict[str, Any]) -> dict[str, Any] | None:
        """Return the prior negative record for this exact config, if any."""
        sig = config_signature(config)
        for rec in self.all():
            if rec.get("config_signature") == sig:
                return rec
        return None
