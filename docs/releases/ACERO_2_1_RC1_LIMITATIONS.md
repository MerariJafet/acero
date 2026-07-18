# ACERO 2.1.0-rc1 — Limitations

Honest boundaries. Nothing here is hidden to make the release look stronger.

- **No discovery.** Recovering Kepler-8b is recovery of a KNOWN planet, not a
  discovery. Injected signals are pipeline tests, not observations.
- **Transit pipeline abstains.** The naive BLS-SNR pipeline does NOT control
  red-noise / eclipsing-binary / cosmic-ray false positives (FPR ~0.4 on nulls),
  so the Abstention Engine abstains from even the bounded claim. This is a
  preserved negative result, not a defect to hide.
- **No external replication.** Same-author, same-data local re-runs reach at most
  `INDEPENDENT_PROCESS_REPRODUCTION`. Two/three methods over the same data are not
  independent replication.
- **Self-evaluation is not independent evaluation** — it uses ACERO's own benchmarks.
- **External review is prepared, not performed.** ACERO never contacts reviewers,
  sends, or publishes.
- **Two astronomy studies only** (sunspots, transit); instrument/pipeline
  dependence not exhaustively assessed.
- **Portal is a modular vanilla-JS SPA** (per ADR-PORTAL-STACK-V2), single local
  user model; no complex multi-tenancy.
- **Runtime** uses real multiprocess workers over on-disk SQLite; no long-lived
  daemon; PostgreSQL is optional and less exercised than SQLite.
- **E2E requires a browser binary**; without it the E2E tests skip (they do not run).
