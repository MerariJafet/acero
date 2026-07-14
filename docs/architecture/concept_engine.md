# Concept Engine (Sprint 8.5)

`cognitive/concepts/`. A concept's meaning is stored STRUCTURALLY, not as a paragraph.

## ScientificConcept
canonical_name, aliases, concept_type (20 types: ENTITY…MATHEMATICAL_STRUCTURE),
domain, abstraction_level, a `DefinitionSet` (lexical / operational / mathematical /
causal / behavioral / by_constraints), mathematical_representation, units,
dimensions, variables/parameters, assumptions/constraints/invariants/symmetries,
examples/counterexamples, `applicable_regimes` and `invalid_regimes`
(`ApplicabilityRegime`: scales, ranges, valid/invalid conditions, evidence),
boundary_conditions, `historical_versions` (versioned transformations),
supporting_sources (claimed, `sources_verified=False`).

## Engine (persists as World-Model CONCEPT nodes)
- Typed conceptual dependencies (`ontology.py`): requires, presupposes, derived_from,
  generalizes, specializes, emerges_from, approximates, replaces, breaks_down_when,
  is_dual_to, is_invariant_under. Acyclic relations (requires/presupposes/…) reject cycles.
- Queries: which concepts depend on an assumption? what generalises this? where does
  it break down? is it applicable under given conditions?
- Conceptual transformations are recorded (never auto-marked "progress").
- Compression score = (phenomena + rules_replaced + new_predictions) /
  (assumptions + exceptions + 1) — heuristic, configurable, explainable.
- Concepts from Codex are quarantined as `unverified_concepts()` until verified.

Tests: `tests/unit/test_cognitive_concepts.py`.
