# Scientific Domain Labs (Sprint 10)

Four computational labs — physics, astronomy, genetics, chemistry — that let ACERO reason
CORRECTLY *within* a discipline and recognise when it lacks the knowledge or tools. Not
"knowing everything"; knowing what each science can and cannot conclude.

## Contract (`domains/core/contracts.py`)
`ScientificDomain` declares: ontology, concepts, units, dimensions, scales, models, term
libraries, tools, solvers, datasets, validation rules, **domain gate rules**, a
`SafetyClass`, capabilities (can/cannot/approximations/dependencies/risks/collaboration),
and a learning-requirement kind. Every output is a `DomainResult` with a
**`DomainResultClass`** so a simulation is never inflated into an experimental validation.

## Result classification
`CALCULATION < SIMULATION < STATISTICAL_ASSOCIATION < MODEL_FIT < STRUCTURE_INFERENCE <
MECHANISTIC_HYPOTHESIS < CAUSAL_CLAIM`, plus the `*_VALIDATION` classes that a
computational lab **never** produces. `domains/core/gate_rules.py` blocks: a simulation
claimed as physical validation, an association claimed as causal, and mass/stoichiometry
violations.

## Labs
- **Physics** (`physics/`): extended dimension-aware term library (linear/quadratic/Coulomb
  friction, saturation, forcing, gradient/laplacian), auditable solvers (RK4, symplectic,
  FTCS diffusion, leapfrog wave) with CFL/energy-drift stability flags. 8-case benchmark
  incl. an unstable solver whose instability is DETECTED so the gate rejects false evidence.
- **Astronomy** (`astronomy/`): Lomb–Scargle, autocorrelation, gap/alias/red-noise/FAP
  flags. 8 cases incl. injected/false transits and a "periodicity without mechanism" case
  that ABSTAINS.
- **Genetics** (`genetics/`, safety=RESTRICTED): Hardy–Weinberg, selection/drift,
  population-structure confounding, multiple-testing correction, Hill/latent-variable. 8
  cases; a spurious causal claim is BLOCKED. Dangerous requests (pathogen/virulence/germline/
  reidentification) are refused.
- **Chemistry** (`chemistry/`, safety=RESTRICTED): first/second-order kinetics, reversible
  equilibrium, Michaelis–Menten, Arrhenius, mass conservation, stiffness, non-identifiability.
  Predictions are labelled `COMPUTATIONAL_PREDICTION_NOT_EXPERIMENTALLY_VALIDATED`; a
  stoichiometry violation is BLOCKED. Toxin/explosive/scale-up requests are refused.

## Honesty
Four computational labs are NOT four physical laboratories. Every result is classified;
`*_VALIDATION` is impossible here; each lab declares what it cannot do and what needs
institutional collaboration (any real experiment).
