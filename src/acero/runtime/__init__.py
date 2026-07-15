"""Persistent multiprocess research runtime (Sprint 14).

Real workers, a persistent task queue, leases/heartbeats/checkpoints, cross-process mutation
tokens, idempotency, and restart recovery — so long research runs survive a process or
machine restart without depending on RAM alone. Everything is local (SQLite by default;
PostgreSQL optional) with no mandatory external platform.
"""
