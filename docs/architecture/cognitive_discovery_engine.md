# Cognitive Discovery Engine (Sprints 8.5–8.7)

Three integrated subsystems in `src/acero/cognitive/` that let ACERO represent what
a concept *means*, discover *shared structure* across domains, and build/verify
models from *first principles*. It extends (does not duplicate) the World Model.

## Principle
ACERO distinguishes: information ≠ knowledge ≠ understanding ≠ explanation ≠
analogy ≠ derivation ≠ discovery. A Codex-proposed relation is not a valid analogy
until it passes structural/dimensional/predictive tests; a Codex-proposed derivation
is not valid until SymPy/units/code verify it. Conceptual reorganisations are
versioned, never deleted.

## Subsystems
- **Concept Engine** (`concepts/`): structured meaning — lexical/operational/
  mathematical/causal/behavioral/constraint definitions, applicability regimes,
  typed dependencies (acyclic where required), versioned transformations, a
  heuristic compression score. See `concept_engine.md`.
- **Analogy Engine** (`analogies/`): deep structural correspondence — governing-form
  match, term-role mapping, dimensionless-group correspondence, separate scores
  (surface weighted low), 7 validation tests incl. a sandbox-verified predictive
  transfer. See `analogy_engine.md`.
- **First Principles Engine** (`first_principles/`): dimensional analysis
  (Buckingham Pi), symmetry→conservation, SymPy-verified derivations, constrained
  model search that ranks by more than RMSE. See `first_principles_engine.md`.

## Integration cycle
```
World Model → Concept (structural representation) → Analogy candidate →
Analogy validation → transferred prediction (sandbox) → First-Principles constraints →
candidate models → computational experiment → evidence → World Model update
```
Implemented in `integration/pipeline.py` + `benchmarks/cross_domain.py`. A
structurally supported analogy raises a belief in the World Model; a misleading one
accrues counter-evidence and is preserved as a negative.

## Shared foundation
`cognitive/dimensions.py`: dimensions over the 7 SI base units, quantity algebra,
equation consistency, and Buckingham-Pi via the exact rational null space (SymPy).
This is verifiable math, not LLM text.

## Codex, safety
Codex proposes concepts, analogy candidates, and derivation steps via `complete_json`
with strict schemas (all properties required; maps encoded as pair arrays — OpenAI
structured-output constraints). Every output is verified; Codex is never evidence.
All code runs in the sandbox. See `audit/engine.py` for the adversarial audit.
