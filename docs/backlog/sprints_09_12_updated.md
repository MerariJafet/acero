# Backlog actualizado — Sprints 9 a 12 (tras el Cognitive Discovery Engine)

## Sprint 9 — Tutor científico y aprendizaje humano
- Extiende `pedagogy/` y los conceptos: explicar un concepto por niveles usando su
  `DefinitionSet`, sus regímenes y sus analogías; preguntas socráticas a partir de
  contradicciones/anomalías del World Model.
- Predicción humana previa vs modelo; ruta de aprendizaje conceptual.

## Sprint 10 — Especialización científica (ampliar)
- Representaciones estructurales (`SystemRepresentation`) por dominio para más
  sistemas (química de reacciones, dinámica poblacional, circuitos, óptica) para
  ampliar el catálogo de analogías más allá de ODE-2º-orden y difusión.
- Integrar simuladores de dominio como herramientas de transferencia predictiva.

## Sprint 11 — Evaluación, auditoría y ciencia adversarial (prioritario)
- Formalizar `cognitive/audit` como gate opcional del pipeline.
- Calibración de scores de analogía/derivación (curvas de fiabilidad).
- Detección de "lenguaje profundo sin sustancia" y de afirmaciones de primeros
  principios que son en realidad literatura recordada (la auditoría Codex ya lo señala).

## Sprint 12 — Publicación, colaboración y portal
- Dashboard con las vistas Concept Map / Analogy Map / Derivation Graph /
  Applicability View / Transformation Timeline sobre la API.
- Export de conceptos/analogías/derivaciones con procedencia; revisión humana obligatoria.

## Deuda técnica transversal
- Inferencia de formas estructurales arbitrarias (hoy catálogo).
- Symbolic regression real + optimización bayesiana/evolutiva (interfaces).
- Estado posterior competitivo normalizado entre modelos (heredado del Sprint 8).
- Migraciones Alembic para las tablas de nodos/aristas.
- Métrica de similitud superficial más rica (la basada en tokens da 0 en átomo↔solar).
