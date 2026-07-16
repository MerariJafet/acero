"""Collaboration engine (Sprint 19): workspaces, validation plans, drafts. Never contacts."""

from __future__ import annotations

from typing import Any

from ..discovery.store import DiscoveryStore
from .models import (
    CollaborationWorkspace,
    ExternalValidationPlan,
    ReviewerRole,
    WorkspaceStatus,
)
from .questions import questions_for

WORKSPACE_SCOPE = "_collaboration"

# Draft communications ACERO may PREPARE (never send).
DRAFT_KINDS = (
    "review_request", "collaboration_request", "dataset_request",
    "reproducibility_request", "mentorship_request", "experimental_validation_request",
)


class CollaborationEngine:
    def __init__(self, store: DiscoveryStore) -> None:
        self._store = store

    def create_workspace(self, project_id: str, purpose: str, *,
                         expertise: list[ReviewerRole] | None = None,
                         license: str = "unspecified") -> CollaborationWorkspace:
        ws = CollaborationWorkspace(
            project_id=project_id, purpose=purpose,
            requested_expertise=expertise or [ReviewerRole.SKEPTICAL_GENERALIST],
            review_questions=questions_for(), license=license)
        self._store.put(WORKSPACE_SCOPE, "workspace", ws.workspace_id, ws.model_dump(),
                        status=ws.status.value, summary=f"workspace: {purpose[:40]}")
        return ws

    def set_status(self, workspace_id: str, status: WorkspaceStatus) -> CollaborationWorkspace:
        raw = self._store.get(workspace_id)
        if raw is None:
            raise KeyError(workspace_id)
        ws = CollaborationWorkspace(**raw)
        ws.status = status
        self._store.put(WORKSPACE_SCOPE, "workspace", ws.workspace_id, ws.model_dump(),
                        status=status.value, summary=f"workspace -> {status.value}")
        return ws

    def workspaces(self) -> list[CollaborationWorkspace]:
        return [CollaborationWorkspace(**r)
                for r in self._store.list_objects(WORKSPACE_SCOPE, kind="workspace")]

    def draft_communication(self, kind: str, *, purpose: str, materials: list[str],
                            reviewer_time_estimate: str, limitations: list[str]
                            ) -> dict[str, Any]:
        """Prepare a DRAFT (never sent). Includes AI-use + no-overclaim statement."""
        if kind not in DRAFT_KINDS:
            raise ValueError(f"unknown draft kind {kind!r}; have {DRAFT_KINDS}")
        return {"kind": kind, "purpose": purpose,
                "reviewer_time_estimate": reviewer_time_estimate, "materials": materials,
                "questions": questions_for(), "limitations": limitations,
                "ai_use": "ACERO assisted; ACERO is not an author and claims no discovery.",
                "no_overclaim": "This is preparation for review, not a claim of validation.",
                "sent": False, "note": "DRAFT ONLY — ACERO never sends anything."}

    def validation_plan(self, claim: str, *, expertise: list[ReviewerRole],
                        facility: str = "", data: str = "", experiment: str = "",
                        blockers: list[str] | None = None) -> ExternalValidationPlan:
        """A PLAN for external validation. A plan is NOT validation; nothing is performed."""
        return ExternalValidationPlan(
            claim=claim, required_expertise=expertise, required_facility=facility,
            required_data=data, required_experiment=experiment,
            blockers=blockers or ["no external collaborator engaged; validation not performed"])
