# Astronomy Lab

**Scope:** light curves, periodicity/quasiperiodicity, transits, orbits, basic spectra,
irregular series, change detection, population stats. Safety: LOW.

**Methods:** Lomb–Scargle (uneven sampling), autocorrelation, gap detection, aliasing and
red-noise flags, a false-alarm-probability WARNING. Orbital checks use the two-body Kepler
approximation with declared limits.

**Datasets (gated, ≤500 MB, hashed, gitignored):** SILSO sunspots, NASA Exoplanet Archive,
synthetic curves. (Kepler/TESS/Gaia subsets are permitted under the same download policy.)

**Benchmark (8):** known period, quasiperiodic, gaps/irregular, aliasing (WARN not
conclude), red noise, false transit (not claimed), injected transit (recovered),
periodicity-without-mechanism (ABSTAINS).

**Gate rules:** association_not_causal.

**Limitations:** a periodic peak is a PATTERN, never a mechanism; no planet confirmation
without follow-up; aliasing can masquerade as signal.
