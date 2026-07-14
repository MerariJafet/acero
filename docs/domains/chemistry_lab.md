# Chemistry Lab (RESTRICTED)

**Scope (computational, low-risk):** kinetics, thermodynamics, public molecular properties,
safe MD, educational docking, small quantum chemistry, abstract reaction networks.

**FORBIDDEN (never implemented, and screened):** toxin/explosive/drug design, hazardous
synthesis, scale-up, harmful lab instructions, weaponization.

**Models:** first/second-order kinetics, reversible equilibrium, Michaelis–Menten,
Arrhenius, mass/charge conservation. Every prediction is labelled
`COMPUTATIONAL_PREDICTION_NOT_EXPERIMENTALLY_VALIDATED`.

**Benchmark (8):** first-order kinetics (half-life), reversible reaction (Keq), Michaelis–
Menten (→Vmax), Arrhenius (k↑ with T), mass conservation (drift <1e-6), stiff system
(instability detected), non-identifiable parameter (only k₁·k₂ observable), and a
stoichiometry violation — **BLOCKED**.

**Gate rules:** mass_conserved, stoichiometry_respected, units_consistent.

**Limitations:** well-mixed / QSSA / single-barrier approximations; a computational
prediction is not experimental validation.
