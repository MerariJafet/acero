# Backlog Sprints 11–12 (actualizado tras Sprint 10)

Estado: Sprints 1–10 implementados y verificados.

## Sprint 11 — Robustez del gate in-line + cobertura de escritura
- Extender `require_context` a TODAS las rutas de escritura (DiscoveryStore,
  UnderstandingStore, ledger), no solo el World Model.
- Contexto de gate seguro para async/subprocesos (hoy thread-local; documentado).
- Migraciones Alembic para las tablas nuevas.
- Robustez numérica entre entornos (tolerancias explícitas).

## Sprint 12 — Preparación para publicación (siempre con revisión humana)
- Gate de publicación conectado a export local revisado (sin publicación automática).
- Ampliar clases/checkers de dominio y datasets públicos (TESS/Kepler/Gaia).
- Grader semántico con verificación adicional de fragmentos citados a nivel de frase.

## Deuda transversal
Ver `docs/backlog/sprints_10_12_updated.md` y `sprints_09_12_updated.md`.
