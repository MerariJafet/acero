# Inline Global Epistemic Gate (Sprint 10)

The gate no longer merely reports — it PHYSICALLY prevents a defective artifact from
advancing.

## Enforcement contract (`epistemic_gate/enforcement.py`)
`enforce()` is the single path a protected mutation takes:

    validate → run gate rules → block-or-continue → mutate → record gate result + provenance

The mutation runs ONLY after the gate passes (or a valid override is recorded). On a block
NO mutation happens and a separate rejection record is kept (the attempt is never lost).
`GateProtectedAction` captures action/stage/artifact/rules/result/allowed/override/provenance.

## Transactional safety (`transaction.py`)
A blocked or failed mutation leaves no partial state: the gate runs BEFORE the write, and a
`Transaction` rolls back compensating actions on failure. A thread-local **gate context** is
opened only after a pass; `require_context()` raises `BypassDetected` if a protected raw
write is attempted outside that window (enforcement is opt-in via `ENFORCE_INLINE_GATE`,
enabled by the guarded wrappers so legacy paths stay working).

## Overrides (`OverridePolicy`, `NON_OVERRIDABLE_RULES`)
`NO_OVERRIDE / HUMAN_OVERRIDE_ALLOWED / ADMIN_OVERRIDE / REQUIRES_EXTERNAL_REVIEW`. Some
rules are **never** overridable: invented citation, fabricated/leaked result, exposed
secret, unsafe execution, lost provenance, retroactive unrecorded edit, false authorship,
deleting negatives, Codex-as-evidence, absolute-truth claim, and publication integrity
(citations verified, reproducible, discovery human-reviewed, conclusion understood). A valid
override records responsible/reason/risk/rules/timestamp/scope/expiry.

## Observability & bypass detection
`middleware.GateMetrics` counts evaluated/allowed/blocked/warnings/overrides/rollbacks/
bypass-attempts and top-triggered rules; `GateTrace` keeps recent protected actions.
`benchmarks/gate_bypass.py` attempts seven bypasses — ALL blocked.

## Known limitations (from the real Codex audit)
- The runtime guard currently protects the World-Model "accepted knowledge" mutations
  (`update_belief`, `link`); extending `require_context` to every store is Sprint 11.
- The gate context is thread-local; it does not propagate across async tasks or
  subprocesses (the sandbox already runs in a separate process). Documented, not hidden.
