# Sprint 8 — World Model Engine · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-sprint-8-world-model`

## Entregables
- **Grafo epistémico persistente y versionado** (`world_model/graph.py`,
  tablas `world_nodes`/`world_edges`/`world_node_history`): 30 tipos de nodo, 22
  tipos de relación. `link` idempotente; relaciones se **debilitan** (inactivan),
  no se borran; beliefs se **actualizan y versionan**, no se sobrescriben.
- **Todo es una creencia** (`belief.py`): `BeliefState` (confidence, evidence,
  counter, replication, negatives, contradictions, sources, historial) con
  `BeliefPolicy` configurable, suavizado bayesiano y `max_confidence<1` (sin
  verdades absolutas).
- **Motor de contradicciones** (`contradictions.py`): detecta creencias
  incompatibles, crea nodo Contradiction y **abre una Question**, penaliza ambas.
- **Motor de anomalías** (`anomalies.py`): registra esperado vs observado,
  convierte explicaciones candidatas en hipótesis, abre OpenProblem; **nunca borra**.
- **Memoria científica** (`queries.py`): experimentos que apoyan/contradicen,
  hipótesis surgidas, modelos que dependen de un supuesto no probado, fallos,
  anomalías abiertas, creencias no probadas, relaciones débiles, claims de una sola
  fuente, supuestos críticos.
- **Programas de investigación** (`programs.py`), **evolución del conocimiento**
  (`evolution.py`: believe_more/less/same, nuevas contradicciones/anomalías,
  siguiente investigación), **narrador** (`narrate.py`: las frases del "criterio final").
- **Integración** (`update.py`): un resultado del Discovery Engine cambia el grafo
  (winner ↑, overfitter ↓ y su relación `explains` debilitada, todos los modelos
  aprenden de su ajuste; contradicciones por stance; anomalía si winner≠oculto).
- **Dato real** (`ingest.py`): NASA Exoplanet Archive → Kepler (slope≈0.999,
  R²≈0.999 sobre ~2.900 planetas) mueve la creencia de la ley. Ver
  `docs/benchmarks/kepler_exoplanets.md`.
- **Visualización HTML** offline (`viz.py`): nodos por tipo, color=confianza,
  aristas rojas=contradice, punteadas=debilitada; paneles de contradicciones,
  anomalías, supuestos críticos, claims de una fuente, relaciones débiles.
- CLI (`acero world demo|stats|narrate|viz|query`) + API (`/world/*`).

## Criterio final (ACERO lo dice)
En una corrida real:
- *"'Kepler's third law' gained support because 1 independent experiment favoured
  it (confidence 0.58)."*
- *"The next experiment '…' has the highest scientific value because it bears on 4
  models involved in open contradictions."*
Y, con más investigaciones, *believe_more* muestra hipótesis que subieron por
replicación independiente; el narrador reporta supuestos críticos no probados y
contradicciones entre programas.

## Auditoría adversarial (Codex real, 15 hallazgos)
Correcciones verificables aplicadas con pruebas de regresión:
- **Relaciones redundantes** → `link` idempotente (sin aristas duplicadas activas).
- **Aprendizaje disperso** → todos los modelos actualizan su creencia según su ajuste.
- **Grafo estático** → la relación del modelo invalidado se **debilita** (inactiva).
- Auditor de reglas detecta ciclos `depends_on`, self-loops, pérdida de historial,
  exceso de `related_to`, y si el grafo "no aprende".
Hallazgos arquitectónicos más profundos (posterior competitivo normalizado,
ontología temporal más rica, cadenas `derived_from` profundas, aristas
question→experiment) quedan documentados como backlog (ADR-0005).

## Calidad
- **241 pruebas, todas verdes** (+47 del World Model: belief, graph, contradictions,
  anomalies, memory, integration, audit, property). ruff + mypy limpios, `make verify` ok.
- ~1.500 LOC en `world_model/`.

## Criterios de aceptación
Actualización de creencias, contradicciones, anomalías, versionado, persistencia,
consultas, propagación, historial, integridad, visualización — **todos probados**.
El World Model responde preguntas sobre investigaciones pasadas (memoria científica).

## Limitaciones / deuda
- Detección de contradicciones por stance estructural (no semántica libre).
- Sin estado posterior normalizado entre modelos competidores (backlog).
- Migraciones Alembic pendientes para las tablas nuevas.
