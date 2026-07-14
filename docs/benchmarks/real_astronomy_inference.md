# Real Astronomy Inference — SILSO Sunspots

Source: `benchmarks/real_astronomy_inference.py`. A genuine public-domain astronomical
time series used to test periodicity / quasiperiodicity / regime detection on real,
noisy data — NOT to discover anything.

## Dataset
- **Source:** SILSO / WDC-SILSO (Royal Observatory of Belgium), monthly mean total
  sunspot number, since 1749. URL `https://www.sidc.be/SILSO/INFO/snmtotcsv.php`.
- **License:** public domain. **Reference:** SILSO (Clette & Lefevre).
- **Size:** ~126 KB, ~3,300 monthly points. Download gated (`authorized=True`), SHA-256
  recorded, CSV gitignored.

## Analysis & results
- **Dominant period ≈ 11.2 years** (FFT) — the solar cycle, recovered from real data.
- Cycle length varies (~9–14 yr) and amplitude varies strongly → classified
  **quasiperiodic**, not a clean sinusoid.
- **Low-activity regime detected around 1809–1819** (the Dalton Minimum).
- Missing months are recognised; uncertainty is recorded.

## What cannot be concluded
- The physical DYNAMO mechanism cannot be inferred from this series alone.
- No future cycles or predictions are claimed.
- The dominant period is an estimate with uncertainty, not a law.
- The activity minima are OBSERVED regimes, not explained.

```bash
acero inference sunspots
```
