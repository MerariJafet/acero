"""Persistent runtime store (Sprint 14).

Durable state for the queue, leases, checkpoints, cross-process token spend, and the
recovery/observability event log — SQLite by default (PostgreSQL works via the same
SQLAlchemy models). All timestamps are ISO strings via the central clock.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..core.clock import now_iso
from ..ledger.models import RuntimeEventRow, RuntimeTaskRow, RuntimeTokenRow


class RuntimeStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    # --- tasks ----------------------------------------------------------
    def put_task(self, task_id: str, kind: str, *, project_id: str = "_",
                 payload: dict[str, Any] | None = None, priority: float = 0.5,
                 idempotency_key: str | None = None, max_attempts: int = 3) -> dict[str, Any]:
        with self._sf() as s:
            if idempotency_key is not None:
                existing = s.execute(
                    select(RuntimeTaskRow).where(
                        RuntimeTaskRow.idempotency_key == idempotency_key)
                ).scalar_one_or_none()
                if existing is not None:
                    return _task_dict(existing)          # idempotent: return the prior task
            row = RuntimeTaskRow(
                id=task_id, project_id=project_id, kind=kind, status="QUEUED",
                priority=priority, payload=payload or {}, checkpoint={}, attempts=0,
                max_attempts=max_attempts, idempotency_key=idempotency_key,
                created_at=now_iso(), updated_at=now_iso())
            s.add(row)
            s.commit()
            return _task_dict(row)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._sf() as s:
            row = s.get(RuntimeTaskRow, task_id)
            return _task_dict(row) if row else None

    def tasks(self, *, status: str | None = None) -> list[dict[str, Any]]:
        with self._sf() as s:
            stmt = select(RuntimeTaskRow)
            if status:
                stmt = stmt.where(RuntimeTaskRow.status == status)
            return [_task_dict(r) for r in s.execute(stmt).scalars().all()]

    def update_task(self, task_id: str, **changes: Any) -> dict[str, Any]:
        with self._sf() as s:
            row = s.get(RuntimeTaskRow, task_id)
            if row is None:
                raise KeyError(task_id)
            for k, v in changes.items():
                setattr(row, k, v)
            row.updated_at = now_iso()
            s.commit()
            return _task_dict(row)

    # --- tokens (cross-process replay protection) -----------------------
    def record_token(self, token_id: str, action: str, project_id: str) -> None:
        with self._sf() as s:
            if s.get(RuntimeTokenRow, token_id) is None:
                s.add(RuntimeTokenRow(token_id=token_id, action=action,
                                      project_id=project_id, spent=False,
                                      issued_at=now_iso()))
                s.commit()

    def is_spent(self, token_id: str) -> bool:
        with self._sf() as s:
            row = s.get(RuntimeTokenRow, token_id)
            return bool(row and row.spent)

    def spend_token(self, token_id: str) -> bool:
        """Mark a token spent; return False if it was already spent (replay)."""
        with self._sf() as s:
            row = s.get(RuntimeTokenRow, token_id)
            if row is None:
                s.add(RuntimeTokenRow(token_id=token_id, action="", project_id="",
                                      spent=True, issued_at=now_iso(), spent_at=now_iso()))
                s.commit()
                return True
            if row.spent:
                return False
            row.spent = True
            row.spent_at = now_iso()
            s.commit()
            return True

    # --- events ---------------------------------------------------------
    def log_event(self, kind: str, *, task_id: str | None = None,
                  decision: str | None = None, detail: str = "",
                  worker_id: str | None = None, run_id: str | None = None) -> None:
        with self._sf() as s:
            s.add(RuntimeEventRow(task_id=task_id, kind=kind, decision=decision,
                                  detail=detail, worker_id=worker_id, run_id=run_id,
                                  at=now_iso()))
            s.commit()

    def events(self, *, task_id: str | None = None) -> list[dict[str, Any]]:
        with self._sf() as s:
            stmt = select(RuntimeEventRow).order_by(RuntimeEventRow.id)
            if task_id:
                stmt = stmt.where(RuntimeEventRow.task_id == task_id)
            return [{"kind": e.kind, "decision": e.decision, "detail": e.detail,
                     "task_id": e.task_id, "worker_id": e.worker_id, "at": e.at}
                    for e in s.execute(stmt).scalars().all()]


def _task_dict(row: RuntimeTaskRow) -> dict[str, Any]:
    return {"id": row.id, "project_id": row.project_id, "kind": row.kind,
            "status": row.status, "priority": row.priority, "payload": dict(row.payload),
            "checkpoint": dict(row.checkpoint), "result": row.result, "error": row.error,
            "attempts": row.attempts, "max_attempts": row.max_attempts,
            "idempotency_key": row.idempotency_key, "lease_owner": row.lease_owner,
            "lease_expires_at": row.lease_expires_at, "heartbeat_at": row.heartbeat_at,
            "created_at": row.created_at, "updated_at": row.updated_at}
