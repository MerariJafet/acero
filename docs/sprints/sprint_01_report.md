# Sprint 1 — Fundación, constitución y control · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-sprints-1-4`

## Entregables
- Auditoría de entorno (`docs/environment/environment_audit.md`) y de repositorio
  (`repository_audit.md`).
- Estructura del monorepo (monolito modular, `src/acero/`), paquete instalable
  (`pyproject.toml`).
- **Constitución** (`docs/governance/ACERO_CONSTITUTION.md`) y **matriz de
  autonomía** (`autonomy_matrix.md`).
- **Políticas versionadas** (`policies/*.yaml`: autonomy, costs, data_access,
  execution, publication, research_safety) + cargador/validador y **PolicyGuard**
  (circuit breaker de costos, guardas de autonomía/publicación/seguridad).
- Configuración por capas (`configs/default.yaml` + `development.yaml` + env vars)
  validada con Pydantic; `.env.example` sin secretos.
- Logging estructurado (structlog + fallback).
- **CLI** (`acero doctor|policy|project|pilot|serve|test|version`).
- **API** (`GET /health`, `/version`, `/policies`, `/projects...`).
- **Sandbox base** (screening + runner restringido).
- **`make verify`** = lint + typecheck + policy + schemas + test.

## Criterios de aceptación
| Criterio | Evidencia |
|---|---|
| El proyecto instala | `pip install -e .` → `acero 0.4.0` ✓ |
| El API inicia | `create_app()` + test `test_health` 200 ✓ |
| El CLI responde | `acero doctor` → exit 0, `OK ✓` |
| Las configuraciones se validan | Pydantic `Config`; `test_config_defaults_and_db_url` |
| Políticas cargadas desde archivos | `test_all_policies_load` (6/6) |
| No se puede activar pago por accidente | `test_paid_llm_disabled_by_default`, `test_cost_guard_*` |
| Suite de pruebas funcional | 81 tests, todos verdes |
| Comando único de validación | `make verify` → "all checks passed" |

## Pruebas
`tests/unit/test_config_policies.py` (9), `test_ids_hashing.py` (5),
`tests/integration/test_api.py` (3). Lint (ruff) y tipos (mypy) limpios.

## Pendientes / deuda
- Alembic real para migraciones en producción (hoy `create_all` idempotente).
- Frontend React (Sprint 12).
