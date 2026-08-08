"""Persistence for Discovery Engine objects, with provenance via the ledger.

Stores candidates, experiment proposals, research-tree nodes, generated tools, and
negative-result records in the generic ``discovery`` table. Every write emits a
provenance event through the existing ResearchLedger so all discovery decisions are
auditable. Negative records and rejected candidates are NEVER deleted.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..core.errors import IntegrityError
from ..ledger.models import DiscoveryRow
from ..ledger.service import ResearchLedger
from ..provenance.events import ProvenanceAction


class DiscoveryStore:
    def __init__(self, session_factory: sessionmaker[Session], ledger: ResearchLedger) -> None:
        self._sf = session_factory
        self.ledger = ledger

    # --- generic put/get ------------------------------------------------
    def put(self, project_id: str, kind: str, obj_id: str, payload: dict[str, Any],
            *, status: str = "", parent_id: str | None = None,
            action: ProvenanceAction = ProvenanceAction.CREATE, actor: str = "system",
            summary: str = "") -> None:
        with self._sf() as s:
            row = s.get(DiscoveryRow, obj_id)
            if row is None:
                s.add(DiscoveryRow(id=obj_id, project_id=project_id, kind=kind,
                                   status=status, parent_id=parent_id, payload=payload))
            else:
                row.payload = payload
                row.status = status or row.status
                if parent_id is not None:
                    row.parent_id = parent_id
            s.commit()
        self.ledger.record_event(
            project_id, action, actor, summary or f"{action.value} {kind} {obj_id}",
            {"kind": kind, "status": status}, entity_id=obj_id,
        )

    def get(self, obj_id: str) -> dict[str, Any] | None:
        with self._sf() as s:
            row = s.get(DiscoveryRow, obj_id)
            return dict(row.payload) if row else None

    def set_status(self, obj_id: str, status: str, *, actor: str = "system",
                   summary: str = "", action: ProvenanceAction = ProvenanceAction.UPDATE) -> None:
        with self._sf() as s:
            row = s.get(DiscoveryRow, obj_id)
            if row is None:
                raise IntegrityError(f"Discovery object {obj_id} not found")
            row.status = status
            payload = dict(row.payload)
            payload["status"] = status
            row.payload = payload
            project_id = row.project_id
            s.commit()
        self.ledger.record_event(project_id, action, actor,
                                 summary or f"status -> {status}", {"status": status},
                                 entity_id=obj_id)

    def list_objects(self, project_id: str, kind: str | None = None,
                     status: str | None = None, parent_id: str | None = None
                     ) -> list[dict[str, Any]]:
        with self._sf() as s:
            stmt = select(DiscoveryRow).where(DiscoveryRow.project_id == project_id)
            if kind is not None:
                stmt = stmt.where(DiscoveryRow.kind == kind)
            if status is not None:
                stmt = stmt.where(DiscoveryRow.status == status)
            if parent_id is not None:
                stmt = stmt.where(DiscoveryRow.parent_id == parent_id)
            rows = s.execute(stmt).scalars().all()
            return [dict(r.payload) for r in rows]

    def list_rows(self, project_id: str) -> list[dict[str, Any]]:
        """All rows WITH metadata (id/kind/status/parent_id) — ids are ULIDs, so
        sorting by id is chronological. Used to reconstruct per-hypothesis flows."""
        with self._sf() as s:
            rows = s.execute(
                select(DiscoveryRow).where(DiscoveryRow.project_id == project_id)
            ).scalars().all()
            return [{"id": r.id, "kind": r.kind, "status": r.status,
                     "parent_id": r.parent_id, "payload": dict(r.payload)}
                    for r in sorted(rows, key=lambda r: r.id)]

    def children(self, parent_id: str) -> list[dict[str, Any]]:
        with self._sf() as s:
            rows = s.execute(
                select(DiscoveryRow).where(DiscoveryRow.parent_id == parent_id)
            ).scalars().all()
            return [dict(r.payload) for r in rows]

    def update_payload(self, obj_id: str, changes: dict[str, Any],
                       *, status: str | None = None) -> dict[str, Any]:
        with self._sf() as s:
            row = s.get(DiscoveryRow, obj_id)
            if row is None:
                raise IntegrityError(f"Discovery object {obj_id} not found")
            payload = dict(row.payload)
            payload.update(changes)
            row.payload = payload
            if status is not None:
                row.status = status
                payload["status"] = status
            s.commit()
            return payload

    # --- guardrail: discovery negatives and rejections are never deleted ---
    # `force=True` bypasses it for the human's explicit delete, which archives a
    # memory note to the vault FIRST (see Lifecycle.delete_hypothesis) — so the
    # failure is preserved, just not left cluttering the live board.
    def delete(self, obj_id: str, *, force: bool = False) -> None:
        with self._sf() as s:
            row = s.get(DiscoveryRow, obj_id)
            if row is None:
                raise IntegrityError(f"Discovery object {obj_id} not found")
            if not force and (
                row.kind == "negative"
                or (row.payload or {}).get("status") in {"REJECTED"}
            ):
                raise IntegrityError(
                    "Negative records and rejected candidates cannot be deleted "
                    "(preserve failures). Archive via status instead."
                )
            s.delete(row)
            s.commit()
