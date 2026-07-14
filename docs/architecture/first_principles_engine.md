# First Principles Engine (Sprint 8.7)

`cognitive/first_principles/`. A verifiable environment for reasoning from
constraints — not a replacement for theoretical physics, and it never claims
discoveries.

## Dimensional analysis
`cognitive/dimensions.py`: SI base dimensions, quantity algebra, equation
consistency, and Buckingham-Pi dimensionless groups (exact rational null space).
It discloses that it gives **scaling only**, not the dimensionless constant.

## Symmetry, invariance, conservation
Documented Noether-INSPIRED lookup (time→energy, space→momentum, rotation→angular
momentum, gauge→charge; scale/permutation→none) — associations, not proofs. A
candidate model declares what it conserves/dissipates; `check_conservation` verifies
the required quantities are covered.

## Derivations
`ScientificDerivation` with per-step checks. Codex may propose steps; SymPy verifies
symbolic identities (must simplify to 0) and dimensions are checked. Unresolved steps
are tracked; confidence is capped (<1) — Codex never certifies a derivation.

## Model search
Constrained candidate generation ranked by MORE than RMSE: parsimony, out-of-range
generalisation, constraint/conservation satisfaction. Selects the minimal adequate
model, flags observationally-equivalent models, and proposes a distinguishing
(extrapolation) experiment. Classifies models: prediction ≠ explanation
(phenomenological/effective/mechanistic/causal/fundamental).

Tests: `tests/unit/test_cognitive_first_principles.py`.
