"""Alembic-based database migrations (Sprint 22).

ACERO now uses real Alembic migrations for schema evolution (upgrade/downgrade/current/
history/check), replacing the RC2 create_all-only bootstrap. The baseline migration builds the
full schema so an empty, RC1, or RC2 database can be brought to the current head idempotently.
"""
