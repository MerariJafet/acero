# Sprint 14 — Persistent Multiprocess Research Runtime · Report

**Estado:** ✅ Terminado · **Rama:** `integration/acero-v2-program`

## Backend persistente (`src/acero/runtime/`)
- **store.py** — estado durable (SQLite por defecto; PostgreSQL vía los mismos modelos):
  tareas (`runtime_tasks`), tokens gastados cross-process (`runtime_tokens`), log de eventos
  de recuperación/observabilidad (`runtime_events`). Schema version → 3.
- **queue.py** — cola persistente con **leases + heartbeats**: `claim` (mayor prioridad,
  atómico, reclama leases expirados = RESUME), `heartbeat` (renueva lease + persiste
  checkpoint; rechaza owner ajeno), `complete`/`fail` (RETRY→DEAD_LETTER)/`cancel`,
  `reap_expired` (detecta worker perdido).
- **worker.py** — worker local real: claim → lease → ejecuta handler → checkpoint →
  complete; un fallo del handler se vuelve **fallo durable**, no un crash.
- **recovery.py** — decisiones RESUME / RETRY / ROLLBACK / DEAD_LETTER / HUMAN_REVIEW según
  checkpoint, intentos, mutación parcial, e inconsistencia registro↔artefacto.
- **secrets.py** — secreto HMAC desde entorno (`ACERO_HMAC_SECRET` + key id); modo
  development (efímero, etiquetado) vs production (rehúsa firmar sin secreto); nunca en Git,
  nunca se muestra completo. Tokens de mutación ahora firman con este secreto → verifican
  **cross-process** cuando hay secreto compartido.

## Idempotencia
`enqueue(idempotency_key=…)` deduplica: un re-enqueue devuelve la tarea previa (protege
ingestión/experimentos/resultados). Tokens de un solo uso también a nivel DB
(`spend_token`), bloqueando replay entre procesos y reinicios.

## Observabilidad
`runtime_events` (append-only) con task_id, worker_id, kind, decision, timestamp; consultable
por tarea. Sin plataforma externa obligatoria.

## Chaos benchmark
Persistent Runtime Chaos Gauntlet (`benchmarks/chaos_gauntlet.py`): **12/12** — worker crash,
duplicate worker, lost heartbeat, expired lease, replay, restart, corrupted checkpoint,
partial output, DB lock (serializado), disk-full simulado, timeout, cancellation.

## CLI
`acero secrets init/rotate/status`, `acero worker enqueue/start/status/stop/chaos`.
`acero doctor --deep` ahora valida runtime backend + secret management (ya presentes).

## Calidad
**618 pruebas en verde** (+27), ruff limpio, mypy limpio (261 archivos), `make verify` OK.

## Limitaciones (declaradas)
- El worker **drena sincrónicamente** (no es un daemon de larga vida); un daemon real
  requiere un gestor de procesos externo (`worker stop` es marcador). El modelo persistente
  ya soporta multiproceso: varios `worker start` sobre la misma DB no se pisan (leases).
- Concurrencia real entre PROCESOS separados no se ejercita en tests unitarios (SQLite
  in-memory por test); la exclusión se valida vía leases + tokens DB + serialización.
- Secreto por defecto efímero en development (por diseño); production exige secreto.
