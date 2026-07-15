# Post-v1 Operation Audit (Fase 0)

## What starts / works
- `make setup` — venv (system-site-packages) + editable install.
- `make verify` — ruff + mypy + policy + schema + pytest (586 tests). ✅
- CLI (`python -m acero.cli.main`): doctor, policy, project, domain, pilot, hypothesis,
  experiment, discovery, benchmark, world, cognitive, inference, learner, learn, gate,
  domains, reliability, publication. Smoke-tested.
- API (`acero serve`, FastAPI): health/version/policies/projects + read-only engine
  endpoints + reliability/publication read endpoints.

## Persistence / state
- SQLite at the configured path; `init_db` creates tables idempotently.
- Real datasets (NASA exoplanets, SILSO sunspots) are gated (`authorized=True`), hashed, and
  gitignored under `research/datasets/*.csv`.
- Export artifacts under `research/artifacts/` are gitignored.

## Requires Docker / Codex / online
- Docker: only the hardened sandbox backend (`ACERO_SANDBOX_BACKEND=docker`); subprocess is
  the default and works offline.
- Codex CLI: only for real LLM proposals/audits (`ACERO_LLM_PROVIDER=codex`); MockProvider is
  the offline default.
- Online: only gated dataset downloads; everything else runs offline.

## What breaks after restart (Sprint 14 target)
- In-process gate contexts and mutation tokens do not survive a process restart (by design in
  v1; per-process secret). Sprint 14 adds a persistent runtime backend + secret management so
  long/multiprocess runs survive restarts.

## Fallbacks
- No Docker → subprocess sandbox (tested). No Codex → MockProvider (deterministic, tested).
- No network → gated downloads skipped; offline benchmarks/tests run.
