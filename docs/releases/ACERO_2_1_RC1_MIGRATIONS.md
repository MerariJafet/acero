# ACERO 2.1.0-rc1 — Migrations

Alembic (programmatic API) with baseline revision `0001_baseline` (schema v3).

## Commands
```
acero db status     # current vs head
acero db upgrade    # apply migrations
acero db check      # verify at head
acero db history    # list revisions
acero db downgrade  # revert (local)
acero db stamp      # stamp head without running
```

## State at release
`acero db status` → `current: 0001_baseline · head: 0001_baseline · up_to_date`.

## Notes
- SQLite engines use WAL + `busy_timeout` so concurrent multiprocess workers wait
  for the write lock rather than raising "database is locked".
- Migrations are the schema-evolution boundary (allowed to import ORM models);
  enforced by the write-surface architecture test.
- Backups record `schema_version`; restore refuses on verification failure.
