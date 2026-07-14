# Pre-chequeo Sprints 5–7 (Discovery Engine)

**Fecha:** 2026-07-13
**Rama de partida:** `feature/acero-sprints-1-4` (commit `431d326`).
**Rama de trabajo creada:** `feature/acero-sprints-5-7-discovery-engine`.

## Estado verificado antes de modificar
- `git status`: árbol limpio, sin cambios sin confirmar (nada que proteger).
- `make verify`: **114 tests en verde**, ruff limpio, mypy sin errores, políticas y
  schemas válidos.
- **Codex CLI**: `codex-cli 0.144.3` disponible; `complete_json` probado en Sprint 4.
- **Sandbox Docker**: imagen `acero-sandbox:py312` presente; backend endurecido
  funcional (`--network=none --read-only --cap-drop=ALL`).
- Entidades epistémicas: 23 tipos; ledger con integridad + procedencia + historial.
- Ciclo reproducible (piloto de enfriamiento) operativo.
- Plugins de dominio: física, astronomía, genética, química (14 benchmarks verdes).

## Componentes reutilizados (no se reconstruyen)
| Necesidad Sprint 5–7 | Se reutiliza |
|---|---|
| Persistir hipótesis/experimentos/nodos | `ledger/` (SQLAlchemy) + nuevas tablas de descubrimiento |
| Procedencia de decisiones | `provenance/` + `ResearchLedger` (evento público nuevo) |
| Generación/crítica LLM estructurada | `llm/providers.CodexCliProvider.complete_json` |
| Ejecución de experimentos | `sandbox/` (subprocess + docker) |
| Prerregistro / escéptico / workflow | `experiment/` (prereg, skeptic, workflow) |
| Reglas de costo/seguridad | `policies/guard.PolicyGuard` |
| Simuladores por dominio | `domains/` |

## Deuda técnica identificada (a considerar, no bloqueante)
- `create_all` idempotente en lugar de migraciones Alembic reales (se documentará
  una migración lógica para las nuevas tablas del Discovery Engine).
- Recuperación semántica aún es BM25; la diversidad de hipótesis usará reglas
  estructurales + similitud léxica (sin embeddings pesados), documentado.
- El escéptico LLM es advisory; se mantiene esa política para todos los críticos LLM.

## Arquitectura elegida para el Discovery Engine
Paquete nuevo `src/acero/discovery/` (estilo monolito modular del repo, no
microservicios): generación → diversidad → falsabilidad → torneo → diseño
experimental → ganancia de información → utilidad → árbol/scheduler/búsqueda →
actualización de confianza → creación de herramientas → siguiente experimento →
supervisor. Persistencia en `ledger/models.py` (tablas nuevas) vía `DiscoveryStore`.
Benchmark en `src/acero/benchmarks/hidden_dynamics.py`.
