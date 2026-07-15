# Universal Inline Gate (Sprint 11)

Extends the Sprint-10 inline gate to every central scientific write path, makes the
execution context async/worker/subprocess-safe, and adds single-use mutation tokens and a
local multi-store Unit of Work.

## Async-safe context (`transaction.py`)
`GateExecutionContext` (context_id, action_id, stage, artifact_ids, allowed_mutations,
policy/rule versions, actor, process_id, parent, created/expires, integrity token) lives in
a `contextvars.ContextVar` stack, so it propagates into asyncio tasks and background tasks
and does NOT leak into worker threads/subprocesses (which start fresh — a worker that must
mutate re-runs the gate). `require_context(where, action=...)` raises `BypassDetected` when
no context is open, or when the open context does not authorise that action.

## Mutation tokens (`tokens.py`)
`enforce()` mints an HMAC-signed, single-use token after a PASS, scoped to one action +
project + artifacts with a short TTL. Validation rejects a tampered, expired, replayed,
wrong-action, wrong-project, or wrong-artifact token. The token authorises only the exact
mutation it was minted for; it never permits a new one.

## Unit of Work (`unit_of_work.py`)
States PREPARED → GATE_PASSED → MUTATING → COMMITTED / ROLLED_BACK / FAILED. A failed step
rolls back the ones already done (no partial confidence, no granted understanding, no lost
negative) and preserves the attempt log.

## Write surface
See `docs/security/write_surface_inventory.md`. No central scientific path is
`LEGACY_UNPROTECTED`. An architectural test (`tests/unit/test_write_surface.py`) fails if a
non-boundary module imports persistence classes directly.

## Limitations (from the real Codex audit)
- The Unit of Work covers local stores; it cannot roll back external/irreversible side
  effects (which is why publication is never automatic).
- The token secret is per-process (tokens do not survive a restart — by design, they are
  short-lived and single-use within a run).
