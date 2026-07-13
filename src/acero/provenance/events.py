"""Provenance events: an append-only trail of what happened, when, and by whom.

Every mutation of the scientific record emits a ProvenanceEvent. The chain lets a
third party reconstruct exactly why the system reached a conclusion.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..core.clock import now_iso


class ProvenanceAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    STATE_CHANGE = "STATE_CHANGE"
    LINK = "LINK"
    RUN_START = "RUN_START"
    RUN_FINISH = "RUN_FINISH"
    REFUTE_ATTEMPT = "REFUTE_ATTEMPT"
    HUMAN_DECISION = "HUMAN_DECISION"
    EXPORT = "EXPORT"


class ProvenanceEvent(BaseModel):
    id: str
    project_id: str
    entity_id: str | None = None
    action: ProvenanceAction
    actor: str = "system"  # 'human', 'system', or an agent name
    at: str = Field(default_factory=now_iso)
    summary: str = ""
    payload_hash: str | None = None
    details: dict = Field(default_factory=dict)
