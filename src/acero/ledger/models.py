"""SQLAlchemy persistence models — the durable scientific record.

A deliberately small schema: a generic ``entities`` table stores typed epistemic
objects as JSON payloads (validated by Pydantic on the way in/out), plus dedicated
tables for projects, runs, provenance, and decisions where relational queries matter.
"""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
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
