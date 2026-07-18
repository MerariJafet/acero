# Exoplanet Transit Signal Robustness — Benchmark

Program: recover a **known** transit (Kepler-8b) robustly and abstain when
unwarranted. **No discovery is claimed.**

## Data (real, public)

| Role | Target | Source | Quarters | SHA-256 (recorded) |
|------|--------|--------|----------|--------------------|
| science | Kepler-8 (KIC 6922244) | MAST public Kepler LC | 3 | per-file in `data_manifests.json` |
| control | KIC 6116048 (quiet) | MAST public Kepler LC | 1 | per-file in `data_manifests.json` |

License: **public domain (NASA/Kepler)**. Total download **1.87 MB** (< 500 MB
per-dataset and < 1.5 GB cumulative limits). Cache gitignored.

## Pipelines (two, over the SAME data — NOT independent replication)

| Pipeline | Detrending | Period statistic | Recovered P | SNR |
|----------|-----------|------------------|-------------|-----|
| A (BLS) | sliding median | Box Least Squares | 3.5218 d | 103 |
| B (PDM) | poly per segment | Phase Dispersion Min. | 3.5218 d | 83 |

Known Kepler-8b period 3.52254 d → **frac error 0.0002**. Pipelines agree to <1%.
Period **stable** across detrending windows (max frac deviation 0.0).

## Signal injection

Grid over depth × period × duration × phase (144 cases): **recovery rate 0.958**.
Calibration (recovery vs injected SNR): SNR 3→0.0, 5→0.0, 7→0.17, 12→1.0, 20→1.0
— low SNR suppressed, high SNR recovered (well-calibrated, monotone).

## Null tests

| Null | Passes (finds nothing)? |
|------|-------------------------|
| flux_shuffled | ✅ |
| control_star (real) | ✅ |
| no_transit_synthetic | ✅ |
| AR(1) red noise | ❌ (spurious detection) |
| inverted_transit | ❌ (dip search mis-locks) |

**FPR = 0.4** — nulls **not fully controlled**. False-positive scenarios:
cosmic-ray outliers, eclipsing-binary-like, and red-noise dips produced false
detections (3 of 5).

## Abstention (the key result)

Even though the known transit is strongly recovered, the Abstention Engine
**ABSTAINS** from the bounded claim because the naive BLS-SNR pipeline does not
control red-noise/artifact false positives (FPR 0.4 > 0.05 allowed). A separate
forced low-SNR case also correctly **ABSTAINS** (SNR 4.9, pipeline disagreement,
low recovery). Both abstentions record their exact reasons.

## Honesty ledger

- **Real data**: the Kepler-8 and control light curves.
- **Injected signal**: all injection/recovery experiments (tests, not observations).
- **Control**: KIC 6116048 (must not show Kepler-8b's period — it does not).
- **Null**: shuffled/AR(1)/synthetic/inverted.
- **NOT a discovery**: recovering Kepler-8b is recovery of a known planet.
- **NOT independent replication**: two pipelines share the same data.
- **Preserved negative result**: red-noise nulls uncontrolled → abstention.

## Clean-room reproduction

Isolated Docker container (`docker/transit_cleanroom/`, fresh OS/Python/cache, no
ACERO internals) re-downloaded the data (hashes match the manifest) and recovered
**P = 3.52326 d** (frac err 0.0002) via an independent code path.
See `docs/benchmarks/transit_cleanroom_docker_output.txt`.
