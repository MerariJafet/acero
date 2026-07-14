# Methodology — Domain Evidence Classification

Every domain output carries a `DomainResultClass`. ACERO never inflates a weaker class into
a stronger one:

`CALCULATION → SIMULATION → STATISTICAL_ASSOCIATION → MODEL_FIT → STRUCTURE_INFERENCE →
MECHANISTIC_HYPOTHESIS → CAUSAL_CLAIM` — and the `*_VALIDATION` classes (PHYSICAL /
BIOLOGICAL / CHEMICAL) which require a real experiment and are therefore **never** produced
by a computational lab.

Enforced by `domains/core/gate_rules.py`:
- a SIMULATION/MODEL_FIT claimed as `*_VALIDATION` → blocked;
- a STATISTICAL_ASSOCIATION with a causal claim → blocked;
- mass/charge/stoichiometry violations → blocked.

This is why "a simulation is not a validation", "an association is not causation", and "a
molecular prediction is not a confirmed synthesis" are structural, not stylistic.
