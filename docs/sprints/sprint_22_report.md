# Sprint 22 — Production-grade Local Runtime · Report

**Estado:** ✅ Terminado · **Rama:** `integration/acero-2.1-program`

## Alembic (migraciones reales, ejecutadas)
- `src/acero/migrations/` (env.py + baseline `0001_baseline`) con API programática
  (`api.upgrade/downgrade/current/check/history/stamp`). CLI `acero db status/upgrade/
  downgrade/check/history/stamp`.
- **Probado de verdad:** base vacía → `upgrade` crea 17 tablas (incl. runtime_tasks,
  world_nodes) → `check` = up_to_date → `downgrade` = base (0 tablas). Idempotente sobre una
  DB `create_all` (RC1/RC2) vía `checkfirst=True` + `stamp`.

## Workers multiproceso (bug real encontrado y corregido)
- El **burn-in** (`benchmarks/runtime_burnin.py`) lanza **procesos OS reales** sobre una
  SQLite en disco y detectó **doble-claim** (2 procesos tomando la misma tarea:
  total_processed=51 > 40). Corregido: `claim()` ahora es un **compare-and-set atómico**
  (UPDATE condicional, gana quien afecta la fila; reintento si rowcount≠1) + `busy_timeout`
  + WAL. Reejecutado: **40 tareas, 4 procesos, 0 duplicación**.
- Casos del burn-in (3/3): multiprocess sin duplicación, enqueue idempotente,
  crash+resume desde checkpoint.

## Config profiles
`development/research/review/production-local/test`. **`production-local` rehúsa iniciar con
un secreto de desarrollo** (`UnsafeProfileStartError`).

## Observability
`runtime/observability.py`: snapshot de métricas (queue depth por estado, dead letters,
eventos) + texto **Prometheus-compatible**; endpoint local `/portal/api/metrics`. Logs JSON
estructurados vía structlog (ya presente). Sin plataforma externa obligatoria.

## Seguridad de runtime
Tests: token falsificado rechazado; lease expirado → tarea reclamada (no perdida); claim
atómico sin doble-claim; endpoint de métricas local.

## Calidad
**716 pruebas en verde** (+15), ruff limpio, mypy limpio (302 archivos), `make verify` OK.

## Limitaciones
El worker CLI drena sincrónicamente (un daemon de larga vida requiere un gestor de procesos
externo); el modelo persistente **ya soporta** multiproceso real (probado). `busy_timeout`/WAL
para SQLite; PostgreSQL usa los mismos modelos. Scheduler avanzado (deadlines/backoff/
maintenance-mode) parcial — leases/retries/dead-letter/cancel presentes.
