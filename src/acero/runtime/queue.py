"""Persistent task queue with leases + heartbeats (Sprint 14).

A worker CLAIMS the highest-priority QUEUED task, taking a time-bounded lease. It heartbeats
while running and persists checkpoints. If a worker dies, its lease expires and the task
becomes reclaimable (RESUME from checkpoint). Completion/failure/dead-letter/cancel are
explicit and durable. Uses a DB row-lock section to keep claims mutually exclusive.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from ..core.clock import now, now_iso
from ..ledger.models import RuntimeTaskRow
from .store import RuntimeStore, _task_dict


@dataclass
class ResearchQueue:
    session_factory: sessionmaker[Session]
    lease_seconds: int = 30
    heartbeat_seconds: int = 10

    def __post_init__(self) -> None:
        self.store = RuntimeStore(self.session_factory)

    def enqueue(self, task_id: str, kind: str, *, project_id: str = "_",
                payload: dict[str, Any] | None = None, priority: float = 0.5,
                idempotency_key: str | None = None, max_attempts: int = 3) -> dict[str, Any]:
        task = self.store.put_task(task_id, kind, project_id=project_id, payload=payload,
                                   priority=priority, idempotency_key=idempotency_key,
                                   max_attempts=max_attempts)
        self.store.log_event("enqueue", task_id=task_id, detail=kind)
        return task

    def claim(self, worker_id: str) -> dict[str, Any] | None:
        """Atomically claim the best claimable task (QUEUED, or LEASED with expired lease)."""
        # Atomic compare-and-set claim: two processes MUST NOT claim the same task. We attempt
        # a conditional UPDATE per candidate and only the process whose UPDATE affects a row
        # wins (rowcount == 1). This is the fix for the multiprocess double-claim the burn-in
        # benchmark caught (Sprint 22).
        while True:
            with self._sf_begin() as s:
                candidates = s.execute(
                    select(RuntimeTaskRow)
                    .where(RuntimeTaskRow.status.in_(("QUEUED", "LEASED", "RUNNING")))
                    .order_by(RuntimeTaskRow.priority.desc())
                ).scalars().all()
                target = None
                for row in candidates:
                    if row.status == "QUEUED" or self._lease_expired(row):
                        target = row
                        break
                if target is None:
                    return None
                target_id = target.id
                resumed = target.status in ("LEASED", "RUNNING")
                prev_status = target.status
                prev_expiry = target.lease_expires_at
                new_expiry = (now() + timedelta(seconds=self.lease_seconds)).isoformat()
                # conditional update guarded on the exact state we read
                res = s.execute(
                    update(RuntimeTaskRow)
                    .where(RuntimeTaskRow.id == target_id,
                           RuntimeTaskRow.status == prev_status,
                           RuntimeTaskRow.lease_expires_at.is_(prev_expiry))
                    .values(status="LEASED", lease_owner=worker_id,
                            lease_expires_at=new_expiry, heartbeat_at=now_iso(),
                            attempts=RuntimeTaskRow.attempts + 1, updated_at=now_iso()))
                if res.rowcount != 1:
                    s.rollback()
                    continue                    # another worker won the race; retry
                s.commit()
                won = s.get(RuntimeTaskRow, target_id)
                task = _task_dict(won)
            self.store.log_event("claim", task_id=task["id"], worker_id=worker_id,
                                 detail="resume" if resumed else "fresh")
            return task

    def heartbeat(self, task_id: str, worker_id: str, *,
                  checkpoint: dict[str, Any] | None = None) -> bool:
        """Renew the lease and persist a checkpoint; False if the lease was stolen/lost."""
        with self._sf_begin() as s:
            row = s.get(RuntimeTaskRow, task_id)
            if row is None or row.lease_owner != worker_id:
                return False
            row.status = "RUNNING"
            row.heartbeat_at = now_iso()
            row.lease_expires_at = (now() + timedelta(seconds=self.lease_seconds)).isoformat()
            if checkpoint is not None:
                row.checkpoint = checkpoint
            row.updated_at = now_iso()
            s.commit()
        return True

    def complete(self, task_id: str, worker_id: str, result: dict[str, Any]) -> bool:
        with self._sf_begin() as s:
            row = s.get(RuntimeTaskRow, task_id)
            if row is None or row.lease_owner != worker_id:
                return False
            row.status = "DONE"
            row.result = result
            row.lease_owner = None
            row.lease_expires_at = None
            row.updated_at = now_iso()
            s.commit()
        self.store.log_event("complete", task_id=task_id, worker_id=worker_id)
        return True

    def fail(self, task_id: str, worker_id: str, error: str) -> str:
        """Record a failure; RETRY if attempts remain, else DEAD_LETTER."""
        with self._sf_begin() as s:
            row = s.get(RuntimeTaskRow, task_id)
            if row is None:
                return "UNKNOWN"
            row.error = error
            row.lease_owner = None
            row.lease_expires_at = None
            if row.attempts >= row.max_attempts:
                row.status = "DEAD_LETTER"
                decision = "DEAD_LETTER"
            else:
                row.status = "QUEUED"
                decision = "RETRY"
            row.updated_at = now_iso()
            s.commit()
        self.store.log_event("fail", task_id=task_id, worker_id=worker_id,
                             decision=decision, detail=error[:200])
        return decision

    def cancel(self, task_id: str) -> bool:
        with self._sf_begin() as s:
            row = s.get(RuntimeTaskRow, task_id)
            if row is None or row.status in ("DONE", "DEAD_LETTER"):
                return False
            row.status = "CANCELLED"
            row.lease_owner = None
            row.updated_at = now_iso()
            s.commit()
        self.store.log_event("cancel", task_id=task_id)
        return True

    def reap_expired(self) -> list[str]:
        """Return tasks whose worker lease expired (lost worker) — reclaimable on next claim."""
        reaped = []
        with self._sf_begin() as s:
            rows = s.execute(
                select(RuntimeTaskRow).where(RuntimeTaskRow.status.in_(("LEASED", "RUNNING")))
            ).scalars().all()
            for row in rows:
                if self._lease_expired(row):
                    reaped.append(row.id)
            s.commit()
        for tid in reaped:
            self.store.log_event("lease_expired", task_id=tid, decision="RESUME")
        return reaped

    # --- helpers --------------------------------------------------------
    def _lease_expired(self, row: RuntimeTaskRow) -> bool:
        if not row.lease_expires_at:
            return False
        try:
            return now() > datetime.fromisoformat(row.lease_expires_at)
        except ValueError:
            return True

    def _sf_begin(self):  # pragma: no cover - thin session ctx
        return self.session_factory()
