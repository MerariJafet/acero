# Methodology — Human Comprehension Gate

Before a CRITICAL decision (accept a hypothesis as priority, discard a model, approve an
expensive experiment, update a core belief, claim novelty, publish, approve a future
physical experiment, interpret a causal conclusion, approve an incomplete derivation), the
gate verifies the human has demonstrated minimum comprehension of the concepts the decision
depends on.

Outcomes: `PASS`, `PASS_WITH_SUPPORT`, `BLOCKED_FOR_LEARNING`, `HUMAN_OVERRIDE`.

- **Low-risk decisions are never blocked** (no paternalism): viewing a result, running a
  local simulation, reading an explanation, generating hypotheses, exporting a local draft.
- **Active HIGH/BLOCKING misconceptions** on a required concept always block until resolved.
- **The human may override any block**, but the override and its reason are recorded (an
  override without a reason is refused).

The gate shows WHICH decision is being made and why it matters; it does not turn the human
into a rubber stamp.
