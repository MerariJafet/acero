# Arquitectura de ACERO — Visión general

ACERO es un **monolito modular** (no microservicios) empaquetado como un único
paquete Python instalable, `acero`, bajo `src/`. Las fronteras entre módulos son
explícitas y se cruzan mediante contratos (Pydantic) y servicios, no estado
compartido.

## Mapa de paquetes

```
acero/
├── core/          # config, logging, ids, hashing, clock, errores
├── policies/      # carga + enforcement de políticas (guard)
├── epistemology/  # tipos, estados, semáforo epistemológico, esquemas Pydantic
├── provenance/    # eventos de procedencia (append-only)
├── ledger/        # persistencia SQLAlchemy + servicio de integridad + export
├── literature/    # ingestión de documentos, chunking, BM25, citas, store
├── evaluation/    # métricas de recuperación (recall@k, MRR, ...)
├── sandbox/       # screening estático + runner restringido
├── experiment/    # workflow, prereg, artifacts, skeptic, pilot, orchestrator
├── pedagogy/      # generador de artefactos de aprendizaje
├── llm/           # proveedores (mock/ollama/paid-gated)
├── cli/           # interfaz Typer
└── api/           # interfaz FastAPI
```

## Flujo de datos (Sprint 4, ciclo completo)

```
Question → Assumptions → Hypotheses (competidoras) → Predictions (prerregistradas)
   → ExperimentPlan → Preregistration(hash) → [aprobación humana]
   → Sandbox run (por semilla) → Artifacts(manifest, env, hashes)
   → Result + NegativeResult → Skeptic(refutación) → Reproducibility(hash match)
   → Claim (limitada, NO descubrimiento) → Learning docs → Report
```

Cada flecha emite un `ProvenanceEvent`. La cadena permite a un tercero
reconstruir qué se hizo, por qué, cuándo, con qué y qué falló.

## Principios de diseño
1. **Local-first.** SQLite + BM25 + mock LLM funcionan sin red ni costo.
2. **Integridad en el servicio, no en el prompt.** Las reglas científicas viven
   en `ledger.service` y máquinas de estado verificables, no en texto de modelos.
3. **Todo hasheable es hasheado.** IDs ordenables por tiempo; artefactos
   direccionados por SHA-256.
4. **Fallbacks sobre fallos.** Docker→subprocess; Ollama→mock; PDF→texto plano.
5. **Interfaces con guarda para lo costoso/peligroso.** Existe la forma, pero
   está bloqueada por política y probada con mocks.

## Persistencia
Tabla genérica `entities` (payload JSON validado por Pydantic) + tablas
relacionales para `projects`, `runs`, `provenance`, `decisions`, `documents`,
`fragments`, e historial (`entity_history`). SQLite por defecto; el `db_url` es
configurable (PostgreSQL/pgvector en fases posteriores). El scaffolding de
migraciones (Alembic) se documenta para producción; en desarrollo se usa
`create_all` idempotente.

Ver decisiones en [`decisions/`](decisions/).
