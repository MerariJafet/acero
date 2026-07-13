# ACERO

**Adaptive Computational Engine for Research and Epistemic Reasoning**

ACERO es un *discovery operating system* local-first y humano-en-el-bucle para
investigación científica computacional. No es un chatbot con herramientas: es una
plataforma que convierte

> curiosidad → pregunta → hipótesis → predicciones → modelos → código →
> experimentos → crítica → evidencia → conocimiento → nuevas preguntas

en un registro **auditable, reproducible y falsable**, donde el investigador
humano es siempre el autor y la autoridad final.

## Estado

Sprints **1–4 implementados y verificados** (81 pruebas en verde; lint y tipos
limpios). Sprints 5–12 planificados. Ver `docs/roadmap/12_sprints.md`.

| Sprint | Tema | Estado |
|---|---|---|
| 1 | Fundación, constitución y control | ✅ |
| 2 | Expediente científico y modelo de conocimiento | ✅ |
| 3 | Biblioteca científica y procedencia | ✅ |
| 4 | Ciclo mínimo de investigación computacional | ✅ |
| 5–12 | Torneo de hipótesis → publicación | ⏳ backlog |

## Principios no negociables

Ver [`docs/governance/ACERO_CONSTITUTION.md`](docs/governance/ACERO_CONSTITUTION.md).
En resumen: ninguna conclusión sin evidencia; ninguna evidencia sin procedencia;
ningún experimento sin predicción previa; ninguna hipótesis aceptada sin intento
de refutación; los resultados negativos se preservan; local-first sin costos
ocultos; ACERO **nunca** se atribuye autoría ni declara descubrimientos.

## Inicio rápido

```bash
# 1. Entorno (reutiliza el stack científico del sistema)
make setup                 # crea .venv y instala acero + herramientas dev
# o manualmente:
python3 -m venv --system-site-packages .venv
./.venv/bin/pip install -e '.[dev]'

# 2. Salud del sistema
./.venv/bin/python -m acero.cli.main doctor

# 3. Gate de calidad (lint + tipos + políticas + schemas + tests)
make verify

# 4. Ejecutar el piloto computacional del Sprint 4
./.venv/bin/python -m acero.cli.main pilot --seeds 1,2,3

# 5. API
./.venv/bin/python -m acero.cli.main serve      # GET /health /version /policies /projects
```

## CLI

```
acero doctor            # auditoría de entorno + políticas
acero policy            # valida las políticas
acero project init      # crea un proyecto de investigación
acero project list      # lista proyectos
acero project export ID # dossier JSON + Markdown + manifest + checksums
acero pilot             # corre el ciclo de investigación del Sprint 4
acero serve             # API FastAPI
acero test              # pytest
```

## Arquitectura

Monolito modular (`src/acero/`): `core, policies, epistemology, provenance,
ledger, literature, evaluation, sandbox, experiment, pedagogy, llm, cli, api`.
Detalle en [`docs/architecture/overview.md`](docs/architecture/overview.md) y ADRs
en `docs/architecture/decisions/`.

## Stack

Python 3.12 · Pydantic v2 · SQLAlchemy 2 (SQLite por defecto) · FastAPI · Typer ·
structlog · NumPy/SciPy/SymPy/scikit-learn · pytest + Hypothesis · ruff · mypy.
Local-first: proveedor LLM `mock` por defecto (Ollama y proveedores de pago detrás
de guardas de política).

## Documentación

- Gobernanza: `docs/governance/`
- Metodología: `docs/methodology/`
- Seguridad: `docs/security/`
- Reproducibilidad: `docs/reproducibility/`
- Reportes de sprint: `docs/sprints/`
- Roadmap y backlog: `docs/roadmap/`, `docs/backlog/`

## Seguridad y alcance

Esta versión **no** realiza experimentación física, biológica, química, humana ni
animal. La ejecución de código ocurre en un sandbox restringido (sin red, sin
secretos, con límites de recursos). Ver `docs/security/`.
