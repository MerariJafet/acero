# Sprints 23–30 — Environment Precheck (FASE 0)

Date: 2026-07-18
Branch: `integration/acero-2.1-program`
Checkpoint tag: `v2.1-pre-portal` (created; baseline green)

## Hardware

| Item | Value |
|------|-------|
| CPU  | 32 logical cores |
| RAM  | 62 GiB total (40 GiB available) |
| Disk | 937 GB volume, **551 GB free** (39% used) |

## Toolchain versions

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12.3 | venv `.venv` with `--system-site-packages` |
| Node   | v22.22.3 | for Playwright |
| npm    | 10.9.8 | |
| Docker | 29.1.3 | available for clean-room / independent-process reproduction |
| Codex CLI | present (`~/.local/bin/codex`) | adversarial audit |

## Git state

- Recent commits: `e7f319e` (Sprint 22), `e4cc1f6` (Sprint 21), `a814fb8` (RC2).
- Tags: `v2.0.0-rc1`, `v2.0.0-rc2`, **`v2.1-pre-portal`** (new checkpoint).
- Working tree: clean.
- Master: untouched. No push. No merge.

## Baseline gate (`make verify`)

- ruff: **All checks passed**
- mypy: **no issues in 302 source files**
- policy: 6 policies valid ✓
- schemas: 33 models up to date ✓
- pytest: **716 passed** in ~95s
- Verdict: **GREEN** — checkpoint tag authorized and created.

## Database / migrations

- `acero db status`: `current: 0001_baseline · head: 0001_baseline · status: up_to_date`
- Alembic programmatic API functional (Sprint 22).

## Browser / Playwright

- Playwright: **NOT installed** (`import playwright` → ImportError). Will install in Sprint 23 §23.2 and launch a real headless browser.
- Node/npm present, so official browser download is feasible.

## Astronomy stack (for Sprint 24)

- astropy: **NOT installed**.
- lightkurve: **NOT installed**.
- Will evaluate installation + record as dependencies in Sprint 24.

## Existing datasets

| File | Size | Program |
|------|------|---------|
| `research/datasets/sunspots.csv` | 124 KB | Sprint 17 SILSO stellar variability |
| `research/datasets/exoplanets.csv` | 141 KB | reference catalog |

Total `research/`: ~940 KB. Ample headroom under the 1.5 GB cumulative limit.

## Network

- MAST (`mast.stsci.edu`): reachable (301 redirect to https).
- STScI archive (`archive.stsci.edu`): reachable (200).
- Kepler/TESS public light-curve download feasible.

## Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Playwright browser download large / flaky | install chromium only; record size; retry; fall back to documented skip if >budget |
| lightkurve pulls heavy transitive deps | evaluate size before install; prefer direct FITS via MAST if lighter; record manifest |
| Light-curve FITS exceeds 500 MB | pick a single quarter/sector; document decision; seek smaller sample |
| Long benchmarks consume session | P0-first (23→26); stop responsibly; never fabricate sprint completion |
| Multiprocess SQLite contention | already hardened (busy_timeout+WAL, atomic claim) in Sprint 22 |

## Download limits (mission constraints)

- Per dataset: **≤ 500 MB**.
- Cumulative new: **≤ 1.5 GB** recommended.
- Every download records: URL, provider, date, license, size, SHA-256, schema, reference, terms, gitignored cache.
- Prohibited: paid services, paid APIs, cloud, publication, public deploy, git push, master merge, third-party contact, account creation.

## FASE 0 verdict

**READY.** Baseline green, tooling present, network up, disk ample. Proceeding to Sprint 23 (Professional Research Portal).
