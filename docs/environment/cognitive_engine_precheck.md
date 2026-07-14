# Pre-chequeo Sprints 8.5–8.7 (Cognitive Discovery Engine)

**Fecha:** 2026-07-13
**Rama de partida:** `feature/acero-sprint-8-world-model` (commit `076c9dd`).
**Rama de trabajo:** `feature/acero-cognitive-discovery-engine`.

## Estado verificado
- `git status`: árbol limpio.
- `make verify`: **241 tests verdes**, ruff + mypy limpios.
- **Codex CLI** `0.144.3`; **imagen Docker** `acero-sandbox:py312` presente.

## Revisión del World Model (a extender, no reconstruir)
- `belief.py` (BeliefState/BeliefPolicy, sin verdades absolutas), `graph.py`
  (nodos/aristas versionados, `link` idempotente, relaciones se debilitan),
  `queries.py` (memoria científica), `contradictions.py`, `anomalies.py`,
  `programs.py`, `evolution.py`, `ingest.py` (dato real), `viz.py`, `audit.py`.
- 30 tipos de nodo (incl. CONCEPT, MODEL, EQUATION, LAW, SYMMETRY-vía-data), 22
  relaciones. **El Cognitive Engine se persiste como nodos/aristas del World Model**
  (extensión), añadiendo relaciones conceptuales nuevas y un paquete `cognitive/`.
- ADR-0005 y backlog Sprint 8 revisados; deuda: falta ontología temporal más rica y
  posterior competitivo normalizado (no bloqueante para este sprint).

## Arquitectura elegida
Monolito modular `src/acero/cognitive/` con tres motores:
- **concepts/**: `ScientificConcept` (definiciones lexical/operacional/matemática/
  causal/comportamiento/restricción), regímenes de aplicabilidad, dependencias
  conceptuales, transformaciones versionadas, compresión heurística; persistido en
  el World Model (nodos CONCEPT + aristas nuevas).
- **analogies/**: `ScientificAnalogy`, comparación estructural/dimensional/
  matemática, scores separados (superficial pesa poco), validación por 7 pruebas,
  transferencia predictiva verificada en sandbox.
- **first_principles/**: análisis dimensional (dimensiones SI, Buckingham Pi,
  validación de ecuaciones), restricciones, simetrías, conservación, `ScientificDerivation`
  con verificación SymPy/numérica, model search por más que RMSE.
- **integration/**: ciclo World Model → Concept → Analogy → First Principles →
  experimento → evidencia → World Model.
- Benchmark: `Cross-Domain Structural Discovery` (oscilador↔RLC, difusión térmica↔
  partículas, y caso negativo átomo↔sistema solar).

## Reglas duras heredadas
Codex nunca es evidencia; toda propuesta (concepto/analogía/derivación) se verifica
por reglas/matemáticas/unidades/código antes de aceptarse. Nada se ejecuta fuera del
sandbox. Reorganizaciones conceptuales se versionan, no se borran.
