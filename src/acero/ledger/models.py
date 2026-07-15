"""SQLAlchemy persistence models — the durable scientific record.

A deliberately small schema: a generic ``entities`` table stores typed epistemic
objects as JSON payloads (validated by Pydantic on the way in/out), plus dedicated
tables for projects, runs, provenance, and decisions where relational queries matter.
"""

from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(64), default="general")
    state: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    created_at: Mapped[str] = mapped_column(String(64))
    principal_investigator: Mapped[str] = mapped_column(String(128), default="human")


class EntityRow(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)  # full validated Pydantic dump


class EntityHistoryRow(Base):
    __tablename__ = "entity_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    at: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    experiment_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="created")
    payload: Mapped[dict] = mapped_column(JSON)


class ProvenanceRow(Base):
    __tablename__ = "provenance"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(64))
    at: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    checksum: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class FragmentRow(Base):
    __tablename__ = "fragments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class WorldNodeRow(Base):
    """World Model node (a belief). Versioned; history in WorldNodeHistoryRow."""

    __tablename__ = "world_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    program_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    label: Mapped[str] = mapped_column(String(512))
    domain: Mapped[str] = mapped_column(String(64), index=True, default="general")
    version: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[float] = mapped_column(Float, default=0.2, index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class WorldNodeHistoryRow(Base):
    __tablename__ = "world_node_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer)
    at: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)


class WorldEdgeRow(Base):
    __tablename__ = "world_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(64), index=True)
    active: Mapped[bool] = mapped_column(default=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class DiscoveryRow(Base):
    """Generic store for Discovery Engine objects (Sprints 5–7).

    ``kind`` discriminates: candidate | proposal | tree_node | tool | negative.
    ``status`` and ``parent_id`` are surfaced as columns for queryable state
    (tournament status, scheduler state, research-tree parent/child).
    """

    __tablename__ = "discovery"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="")
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class SchemaVersionRow(Base):
    """Records the applied schema version (Sprint 13 lightweight migrations).

    ACERO uses SQLAlchemy ``create_all`` (idempotent) rather than Alembic; this table
    records the logical schema version and when it was applied so ``acero doctor --deep``
    can detect a DB created by an older/newer ACERO and refuse to run against a mismatch.
    """

    __tablename__ = "schema_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, index=True)
    applied_at: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, default="")


class RuntimeTaskRow(Base):
    """Persistent research task (Sprint 14): survives restarts, carries lease + checkpoint.

    ``status``: QUEUED | LEASED | RUNNING | DONE | FAILED | DEAD_LETTER | CANCELLED.
    ``lease_owner``/``lease_expires_at`` implement worker leases; ``heartbeat_at`` detects a
    lost worker; ``checkpoint`` persists partial progress for RESUME; ``idempotency_key``
    dedups re-enqueues.
    """

    __tablename__ = "runtime_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True, default="_")
    kind: Mapped[str] = mapped_column(String(48), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="QUEUED")
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    lease_expires_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    heartbeat_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[str] = mapped_column(String(64))


class RuntimeTokenRow(Base):
    """Cross-process record of issued/spent mutation tokens (Sprint 14 replay protection).

    In-process replay is blocked by TokenRegistry; this makes single-use enforcement survive
    across workers and restarts."""

    __tablename__ = "runtime_tokens"

    token_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    spent: Mapped[bool] = mapped_column(default=False, index=True)
    issued_at: Mapped[str] = mapped_column(String(64))
    spent_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RuntimeEventRow(Base):
    """Append-only runtime/recovery event log (Sprint 14 observability)."""

    __tablename__ = "runtime_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(48), index=True)
    decision: Mapped[str | None] = mapped_column(String(24), nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    at: Mapped[str] = mapped_column(String(64))
