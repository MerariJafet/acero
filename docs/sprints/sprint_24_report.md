# Sprint 24 — Exoplanet Transit Signal Robustness Program

Date: 2026-07-18
Branch: `integration/acero-2.1-program`
Status: **complete** · `make verify` green (**766 passed**)

## Objective

ACERO's second real scientific program: recover a KNOWN transit (Kepler-8b) from
public Kepler data robustly against noise, gaps, detrending, multiple testing and
artifacts — and abstain when unwarranted. **No discovery claimed.**

## What was done (executable evidence, not just code)

- **24.1 Target**: Kepler-8 (KIC 6922244), confirmed hot Jupiter Kepler-8b
  (P≈3.5225 d, depth≈0.9%) — well sampled by 29.4-min long cadence. Ultra-short
  Kepler-10b was rejected as poorly sampled by long cadence.
- **24.2 Data**: astropy installed (FITS I/O); light curves downloaded directly
  from the **MAST public archive** (no heavy lightkurve stack — lighter standalone
  package, documented). Science (3 quarters) + **real control star** (KIC 6116048).
- **24.3 Manifest**: `TransitDatasetManifest` records mission/target/quarter/
  cadence/pipeline/columns/license/URL/**SHA-256**/size/missingness/known-artifacts.
  Total 1.87 MB (well under limits). Cache gitignored.
- **24.5 Preregistration**: written and **SHA-256 hashed BEFORE any analysis**
  (`f2ffba25…`); the orchestrator refuses to run if the hash changed.
- **24.6 Hypotheses**: H0–H6 (noise+trend, non-transit periodic, known transit,
  instrumental artifact, red noise, overfit, insufficient data).
- **24.7 Two pipelines**: A = median detrend + **BLS**; B = poly detrend + **PDM**.
  Both recover **P = 3.5218 d** (frac error 0.0002 vs known). Declared NOT
  independent replication (same data).
- **24.8 Injection**: grid recovery 0.958; SNR calibration monotone (low
  suppressed, high recovered).
- **24.9 Nulls**: flux-shuffle ✅, control-star ✅, no-transit ✅; **AR(1) red
  noise ❌**, inverted-transit ❌ → **FPR 0.4**. Phase-randomization declared as a
  shape-null only (not used to test periodicity).
- **24.11 False positives**: cosmic rays, eclipsing-binary-like, red-noise dips
  produce false detections (3/5) — analyzed, not hidden.
- **24.12 Abstention Engine**: **ABSTAINS** on the bounded claim (red-noise nulls
  uncontrolled) AND on a forced low-SNR case — each with recorded reasons. This is
  a **real abstention**, not a formality.
- **24.13 World Model**: `record_as_program` registers the program + a
  non-discovery `ReviewDossier` requiring external review.
- **24.14 Human Understanding**: `transit` curriculum with BLOCKING concepts —
  *recovery_is_not_discovery*, *injection_is_not_observation*,
  *same_data_not_independent*, *when_to_abstain*.
- **24.15 Dossier**: full 15-directory `research_dossier/` tree with preregistration,
  manifests, experiments, nulls, injection, **negative_results (preserved)**,
  reliability, learning, review, publication_candidate (NOT a candidate), tables.
- **24.16 Clean-room**: isolated **Docker** container (fresh OS/Python/cache, no
  ACERO internals) re-downloaded the data (hashes match) and recovered
  P = 3.52326 d via an independent code path. Output committed at
  `docs/benchmarks/transit_cleanroom_docker_output.txt`.

## Key scientific outcome (honest)

The known transit is strongly and reproducibly recovered — **but** the pipeline's
red-noise and artifact nulls are not controlled, so ACERO **abstains** from even
the bounded, non-discovery claim. Recovery ≠ claim. This preserved negative result
and real abstention are the point of the sprint.

## Tests (16 new)

- `tests/unit/test_transit_units.py` (10): prereg hash, injection recovery, nulls,
  calibration, abstention logic, curriculum blocking concepts.
- `tests/integration/test_transit_real_data.py` (6, network/cache-gated): both
  pipelines recover the known period; manifest provenance; control star clean;
  end-to-end no-discovery + dossier; `record_as_program`; clean-room reproduce.

## Honesty declaration

Real data: Kepler-8 + control. Injected: all recovery experiments. Control: KIC
6116048. Null: shuffled/AR(1)/synthetic/inverted. **NOT a discovery. NOT external
replication. Requires human review. Nothing published.**

## Docs

- `docs/benchmarks/exoplanet_transit_robustness.md`
- `docs/benchmarks/transit_cleanroom_docker_output.txt`

Commit: `sprint-24: execute exoplanet transit robustness program`
