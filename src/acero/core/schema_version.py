"""Lightweight schema versioning (Sprint 13).

ACERO persists via SQLAlchemy ``create_all`` (idempotent), not Alembic. This module records
a logical schema version so a database created by an older/newer ACERO can be DETECTED. It
does not rewrite tables; it stamps the version on a fresh DB, and reports a mismatch (which
``acero doctor --deep`` surfaces) rather than silently running against an incompatible store.

Bump ``CURRENT_SCHEMA_VERSION`` whenever a table is added/changed. The v2 baseline (Sprint
13) is version 2; everything before the schema_version table is treated as version 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..core.clock import now_iso
from ..ledger.models import SchemaVersionRow

CURRENT_SCHEMA_VERSION = 3  # Alembic head 0001_baseline (Sprint 22)


@dataclass
class SchemaStatus:
    db_version: int | None            # None ⇒ pre-versioning DB (legacy v1)
    code_version: int
    compatible: bool
    detail: str


def current_db_version(sf: sessionmaker[Session]) -> int | None:
    """Return the highest recorded schema version, or None if the table is empty."""
    with sf() as s:
        rows = s.execute(select(SchemaVersionRow.version)).scalars().all()
    return max(rows) if rows else None


def stamp(sf: sessionmaker[Session], *, version: int = CURRENT_SCHEMA_VERSION,
          note: str = "") -> None:
    """Record ``version`` as applied (idempotent per version)."""
    with sf() as s:
        existing = s.execute(
            select(SchemaVersionRow).where(SchemaVersionRow.version == version)
        ).scalar_one_or_none()
        if existing is None:
            s.add(SchemaVersionRow(version=version, applied_at=now_iso(), note=note))
            s.commit()


def ensure_stamped(sf: sessionmaker[Session]) -> None:
    """Stamp the current version on a DB that has none yet (fresh or migrated-in)."""
    if current_db_version(sf) is None:
        stamp(sf, note="baseline stamp")


def check(sf: sessionmaker[Session]) -> SchemaStatus:
    """Compare the DB's recorded version with the code's expected version."""
    dbv = current_db_version(sf)
    code = CURRENT_SCHEMA_VERSION
    if dbv is None:
        return SchemaStatus(None, code, True,
                            "no schema_version rows (fresh or legacy v1) — will be stamped")
    if dbv == code:
        return SchemaStatus(dbv, code, True, "schema up to date")
    if dbv < code:
        return SchemaStatus(dbv, code, True,
                            f"DB is older (v{dbv} < v{code}); create_all adds new tables "
                            f"idempotently, run 'acero doctor --deep' after upgrade")
    return SchemaStatus(dbv, code, False,
                        f"DB is NEWER (v{dbv} > v{code}) — this ACERO is older than the DB; "
                        f"upgrade ACERO before writing")
