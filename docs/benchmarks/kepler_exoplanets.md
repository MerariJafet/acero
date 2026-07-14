# Real Data: Kepler's Third Law on NASA Exoplanets

Source: `world_model/ingest.py`. First use of a **real** external dataset, to verify
the World Model changes correctly with real data — NOT to claim any discovery.

## Dataset
- **Source:** NASA Exoplanet Archive TAP, table `ps` (default parameter set).
- **Columns:** `pl_name, pl_orbper` (days), `pl_orbsmax` (AU), `st_mass` (M_sun).
- **License:** public domain (NASA/IPAC/Caltech).
- **Reference:** Akeson et al. 2013, PASP 125, 989.
- **Size:** ~140 KB (~2,900 planets after filtering) — far below the 500 MB cap.
- **Provenance:** the exact TAP URL and a SHA-256 of the CSV are recorded on the
  Dataset node. Download requires explicit `authorized=True` (data_access policy).

## Test
Kepler's third law in solar units: `P[yr]² = a[AU]³ / M[M_sun]`. We regress
`log10(P²)` on `log10(a³/M)`; Kepler predicts slope ≈ 1.

**Result on real data:** slope ≈ **0.999**, **R² ≈ 0.9989**, ~99% of planets within
2× of the predicted period. The World Model's belief in Kepler's law moves from the
prior (0.2) toward supported (~0.58 after one dataset; higher with more independent
sources).

## What this demonstrates (and does not)
- ✅ The World Model **changes correctly** with real, noisy, real-format data
  (units, missing values, metadata, provenance, hash, uncertainty).
- ✅ Belief update is evidence-driven and traceable.
- ❌ NOT a discovery: Kepler's third law is textbook physics. Recovering it from
  real data validates the *pipeline*, nothing about the universe that was unknown.
- ❌ No claim about individual "most deviating" planets (measurement/definition
  effects; recorded but not interpreted).

## Run it
```bash
acero world demo --system damped_oscillator --exoplanets
```
