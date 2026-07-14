# Methodology — Gate Transactionality

A protected mutation is atomic w.r.t. the gate: the gate runs BEFORE the write, so a block
means no write ever happened (no partial state, no confidence bump, no accepted relation,
no promotion). The attempt is preserved as a rejection record. On a mutation exception, the
`Transaction` runs compensating rollbacks and the gate context is always closed.

A thread-local **gate context** is the runtime proof that a write passed the gate:
`require_context()` raises `BypassDetected` for a protected raw write attempted outside it.
Enforcement is opt-in (`ENFORCE_INLINE_GATE`) and enabled by the guarded wrappers, so legacy
code keeps working while new writes go through `enforce()`. Limitation: thread-local context
does not cross async/subprocess boundaries (Sprint 11).
