# ACERO 2.1.0-rc1 — Research Programs

## 1. Stellar Variability (SILSO sunspots) — Sprint 17
Real SILSO monthly sunspot number. FFT dominant ~11.19 yr cycle; AR(1) red-noise
surrogate significance; bootstrap cycle CI [10.27, 11.67]. Honesty gate blocks any
discovery claim. A DATA-LEVEL description, not a mechanism, not a discovery.

## 2. Exoplanet Transit Robustness (Kepler-8b) — Sprint 24
Real Kepler-8 (KIC 6922244) + control (KIC 6116048) light curves from MAST
(public domain, hashed manifest, 1.87 MB). Preregistration hashed before analysis.

- Two pipelines (BLS + PDM) both recover **P = 3.5218 d** (0.02% from known).
- Signal injection: recovery 0.958; calibrated (low SNR suppressed, high recovered).
- Null tests: shuffle/control/no-transit pass; **AR(1) red noise + inverted-transit
  NOT controlled** (FPR 0.4); EB-like / red-noise / cosmic-ray scenarios produce
  false detections.
- **Abstention Engine ABSTAINS** from the bounded claim (nulls uncontrolled) and on
  a forced low-SNR case — real abstentions with recorded reasons.

**Neither program claims a discovery.** Both require human review. Nothing published.

Benchmark: `docs/benchmarks/exoplanet_transit_robustness.md`.
