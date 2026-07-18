# ACERO 2.1.0-rc1 — Release Report

Date: 2026-07-18 · Branch: `integration/acero-2.1-program` · **No push, no merge to master.**

## What 2.1 adds over 2.0.0-rc2

- **Professional research portal** (Sprint 23): local auth (PBKDF2 + server
  sessions + CSRF + rate limit), full research workspace flow through protected
  services, scalable World Model explorer (10k nodes, paginated), result cards,
  **real Playwright browser E2E**, WCAG basics, measured performance.
- **Second scientific program** (Sprint 24): exoplanet transit robustness on real
  Kepler-8 data — two pipelines, injection, null tests, false positives, and a
  real **abstention** (no discovery).
- **Independent-process reproduction** (Sprint 25): a standalone package (no ACERO
  internals) reproduced in an isolated Docker container, with an alternative
  implementation, review bundle + tamper detection, and an external-review playbook.
- **Release consolidation** (Sprint 26): acceptance matrix, `acero demo full`,
  100+ task burn-in, security audit, release docs.

## Acceptance

`acero acceptance` → **RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW**, 23/23 rows PASS,
no blockers. `make verify` green. `acero security-audit` → 10/10.

## Quality metrics

- Tests: **781 passing** (ruff + mypy + policy + schemas clean).
- Real browser E2E: 13 flows + negatives (skips only without a browser binary).
- Burn-in: 120 tasks / 4 real worker processes / cancellations / no duplication.
- Gauntlets: reliability 10/10, chaos 12/12, red-team 22/22, mutation 8/8,
  review 6/6, external-review 11/11, self-evaluation NO_REGRESSION.

## Explicitly NOT done (by design)

No discovery claimed. No external replication (only INDEPENDENT_PROCESS_REPRODUCTION).
No publication, no push, no merge to master, no third-party contact. These remain
human decisions.

## Human decisions pending

Merge to master, push, publication, reviewer selection, external validation.
