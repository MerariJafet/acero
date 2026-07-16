"""Baseline schema (ACERO v2 / schema v3).

Revision ID: 0001_baseline
Revises:
Create Date: v2.1

Creates the full ACERO schema from the SQLAlchemy metadata so an empty database is brought to
the current head. Idempotent-friendly: only creates tables that do not already exist (so an
RC1/RC2 database created via create_all can be stamped at this revision without duplication).
"""

from __future__ import annotations

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from acero.ledger.models import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind, checkfirst=True)


def downgrade() -> None:
    from acero.ledger.models import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
