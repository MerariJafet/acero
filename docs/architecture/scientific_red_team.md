# Scientific Red Team (Sprint 11)

A versioned library of scientific attacks — data (leakage, duplicates, wrong units),
statistics (HARKing, optional stopping, miscalibration), models (non-identifiability,
equivalent models, solver artifacts, irreproducibility), literature (fake/retracted/
unsupported citations), human cognition (keyword echo, grader gaming, circular reasoning,
empty confidence), and domain (periodicity-as-mechanism, association-as-causal,
simulation-as-validation, mass-balance violation) — each wired to the REAL ACERO detector.

The runner records `DETECTED / MISSED / PARTIALLY_DETECTED / FALSE_POSITIVE / ABSTAINED` per
attack. Scientific mutation testing mutates a clean artifact (change units, drop baseline/
control, edit prereg, swap dataset, hide a negative) and confirms the gate catches each.
Codex may PROPOSE attacks but can never declare the system safe — every finding becomes a
rule, a test, or a documented limitation.
