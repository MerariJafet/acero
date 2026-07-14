# Governing Structure Inference Engine (Sprints 8.8–8.9)

`src/acero/inference/`. Infers mathematical governing structure from data — not curve
fitting. It reconstructs which terms/relations are present, which quantities are
conserved, where the dynamics change regime, which models are equivalent, and which
experiment would distinguish them; and it ABSTAINS when the data can't tell.

## Principle (declare the level reached)
```
curve_fitting ≠ system_identification ≠ symbolic_regression ≠
governing_equation_discovery ≠ causal_discovery ≠ mechanistic_explanation
```
ACERO reports its `inference_level` and never calls a fitted equation a law.

## Pipeline
```
observations → derivative estimation (data/derivatives) → candidate term library with
filtering (libraries/terms) → sparse identification STLSQ + stability (discovery/
sparse_identification) → invariants (discovery/invariants) → regimes (discovery/
change_points) → identifiability (model_selection/identifiability) → equivalence
(model_selection/equivalence) → discriminating experiment (active_experiments) →
calibration (calibration) → EPISTEMIC GATE (audit/gate) → abstention.
```

## What is inferred vs imposed
Every result lists `imposed` (library families, complexity cap, polynomial ODE ansatz,
derivative method, forbidden terms) and `inferred` (the selected terms + coefficients).
The library is IMPOSED; the structure is identified from it.

## Key components
- **Derivatives** (`data/derivatives.py`): finite differences, Savitzky–Golay, spline;
  each records method, error, and unreliable regions (edges, gaps).
- **Library** (`libraries/terms.py`): family-based (polynomial/interaction default;
  reciprocal/sqrt/log/trig opt-in), filtered by data domain (no 1/x across zero, no
  log/sqrt of non-positive), algebraic duplicates, forbidden terms, complexity.
- **STLSQ** (`sparse_identification.py`): sequential thresholded RIDGE regression
  (ridge suppresses collinear-library blow-up, e.g. when a conserved quantity makes
  {1,x²,v²} dependent), with stability selection over thresholds and bootstraps and a
  threshold-sensitivity report.
- **Invariants**: low-variance feature combinations, classified exact / approximate /
  dataset-specific / artifact, verified under noise (constant term excluded).
- **Regimes**: global-model residual homogeneity (robust to periodic data; no
  false-positive on clean oscillators).
- **Identifiability**: condition number + parameter correlation + data sufficiency →
  IDENTIFIABLE / PARTIALLY / NON / DATA_INSUFFICIENT / REGIME_DEPENDENT.

## Recovery (clean data)
Exponential, logistic (dx/dt=0.8x−0.08x²), harmonic (dx/dt=v, dv/dt=−4x), damped
(−4x−0.5v), predator-prey (1.1x−0.4xy, −0.4y+0.1xy) — all recovered from data with the
equation hidden. Under noise, R² degrades gracefully; with an omitted variable, the
system flags structured residuals rather than inventing certainty.

## Codex
Codex proposes candidate terms (`discovery/symbolic_search.py`, strict schema); every
proposal is validated (SymPy parse + finite on data). A real run proposed `abs(v)*v`
and `sign(v)` (friction terms beyond the polynomial library). Codex is never evidence.
See `audit/engine.py` and `epistemic_gate.md`.
