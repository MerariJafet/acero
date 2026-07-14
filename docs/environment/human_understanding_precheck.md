# Sprint 9 Precheck — Human Understanding Engine + Global Epistemic Gate

- **Branch created:** `feature/acero-human-understanding-engine` (from
  `feature/acero-governing-structure-inference` @ `6d04267`).
- **Baseline:** `make verify` green — 335 tests, ruff + mypy clean.
- **Codex CLI:** present on PATH and at `~/.local/bin/codex`; used real for the pedagogical
  adversarial audit.
- **Docker sandbox:** available (`acero-sandbox:py312`); executable understanding tasks
  reuse it.

## Inspected before building
World Model, Cognitive Engine, Discovery Engine, Inference Engine, the Sprint 8.9 epistemic
gate (`inference/audit/gate.py`, 14 blocker rules), CLI, API, schemas, policies, audits,
and the Sprint 8.8/8.9 reports.

## Technical debt noted (carried, not fixed here)
- Inference libraries are polynomial (catalogued forms).
- Coefficients lack calibrated intervals.
- Token-based surface similarity is weak (from the cognitive backlog).

## Approach
- Reuse the generic `discovery` table (via `DiscoveryStore`) for learner persistence — no
  new Alembic migration.
- Generalize the existing 14 inference-gate rules into a transversal
  `epistemic_gate/` layer; do NOT duplicate contradictory logic (policies bridged, not
  restated).
