# Analogy Engine (Sprint 8.6)

`cognitive/analogies/`. Detects DEEP structure shared across domains; verbal
similarity is weighted low and never decides.

## Representation
A `SystemRepresentation` gives variables (with dimensions), the canonical
`structural_form` of the governing equation, domain-neutral `term_roles`
(inertia/dissipation/restoring/response/flow/forcing, or field/diffusivity/space/time),
invariants, symmetries, and named `dimensionless_groups`.

## Scores (separate, transparent)
structural, mathematical, causal, invariant_preservation, boundary_compatibility,
predictive_transferability, surface_similarity (weight 0.05), failure_risk. The
`deep_score` heuristic (2 dp, uncalibrated) weights deep structure heavily.

## Validation (7 tests)
structural (forms + roles), dimensional (a shared group is dimensionless in BOTH
systems with their own units), mathematical (role isomorphism), limits (shared
conservation + form), predictive_transfer (**simulated in the sandbox**: the
resonance ω₀=sqrt(c/a) peak is measured for both systems), counterexample (surface/
geometric similarity without deep structure ⇒ misleading), skeptic.

## Status
PROPOSED → STRUCTURALLY_SUPPORTED / VALID_IN_REGIME / PARTIALLY_VALID / MISLEADING /
BROKEN / REJECTED. Rejected/misleading analogies are preserved.

## Codex
`candidates.py` proposes a mapping (arrays of {from,to} pairs); ACERO validates it.

Tests: `tests/unit/test_cognitive_analogies.py`, `tests/science/test_cross_domain.py`.
