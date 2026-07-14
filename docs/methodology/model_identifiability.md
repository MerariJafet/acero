# Model Identifiability

`inference/model_selection/identifiability.py`. From the active library we compute the
condition number (parameter correlation), the maximum off-diagonal parameter
correlation, and data sufficiency (samples per parameter) → a status of IDENTIFIABLE /
PARTIALLY_IDENTIFIABLE / NON_IDENTIFIABLE / DATA_INSUFFICIENT / REGIME_DEPENDENT.
Non-identifiable parameters are never presented with false precision, and a
non-identifiable model presented as the unique answer is BLOCKED by the epistemic gate.
Observationally-equivalent models (`equivalence.py`) are not counted as distinct
discoveries; a distinguishing experiment is proposed instead.
