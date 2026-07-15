# Async Gate Context (Sprint 11)

The gate context is stored in a `contextvars.ContextVar` stack, so it propagates correctly
into asyncio tasks and FastAPI background tasks, and does NOT leak into worker threads or
subprocesses (they start with a fresh copy). A worker that legitimately needs to mutate must
re-run the gate to establish a new context — a worker with no context is BLOCKED
(`BypassDetected`), which is the safe default. `require_context(action=...)` also checks the
open context authorises that specific action, so a context opened for one mutation cannot
authorise a different one.
