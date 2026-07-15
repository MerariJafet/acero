# Sprint 16 — Research Program Operating System · Report

**Estado:** ✅ Terminado · **Rama:** `integration/acero-v2-program`

## Qué se construyó (`src/acero/program/`)
De proyectos aislados a **programas científicos** de meses/años.
- **models.py** — `ResearchProgram` (mission, domains, central/instrumental questions,
  theories, models, datasets, subprojects, milestones, risks, compute_budget, budget_usage,
  learning/collaboration/publication plans, status, retrospectives). `StrategicQuestion` con
  roles (central/instrumental/prerequisite/enabling/discarded/paused). `Milestone`,
  `ComputeBudget`, `Retrospective`.
- **portfolio.py** — priorización **multidimensional** (9 dimensiones: information_gain,
  feasibility, novelty_uncertainty, compute_cost, learning_value, data_available, risk,
  dependency_readiness, external_validation_need). Ofrece un ranking pero **muestra todas las
  dimensiones** — sin score único opaco; el humano puede anular el orden.
- **budget.py** — límites **duros**: una carga que excedería un recurso se **rechaza**
  (`BudgetExceeded`, sin carga parcial). Compone con la política de costos (servicios de pago
  siguen gated).
- **engine.py** — persiste programas vía la tabla `discovery` (`kind=research_program`),
  gestiona preguntas/milestones/budget/retrospectivas, y expone una vista estratégica.
  **No crea eventos de calendario externos.**

## Integración
Persistencia por el ledger (procedencia); tipo de nodo `RESEARCH_PROGRAM` ya existente en el
World Model para futura vinculación. Schema `research_program` exportado.

## CLI
`acero program create/list/view/prioritize`.

## Calidad
**630 pruebas en verde** (+12), ruff limpio, mypy limpio (266 archivos), `make verify` OK.

## Criterios de aceptación
Programas persistentes ✓ · portfolio (multidimensional) ✓ · milestones ✓ · budget (duro) ✓ ·
learning plan ✓ · retrospectives ✓ · CLI ✓ · tests ✓ · integración World Model (nodo) ✓.
API/portal se cablearán con el portal (Sprint 15, pendiente).

## Limitaciones
Milestones/calendario son datos locales (ACERO nunca crea eventos externos). La vinculación
program↔subproyectos↔World-Model nodes es por id (no auto-sincronizada aún). El portal
(Sprint 15) y la ejecución de un programa astronómico real completo (Sprint 17) quedan
pendientes.
