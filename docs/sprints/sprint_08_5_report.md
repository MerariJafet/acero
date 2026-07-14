# Sprint 8.5 — Concept Engine · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-cognitive-discovery-engine`

## Entregables
- `ScientificConcept` estructurado (20 tipos; definiciones lexical/operacional/
  matemática/causal/comportamiento/restricción; unidades, dimensiones, invariantes,
  simetrías; regímenes de aplicabilidad válidos/inválidos; transformaciones versionadas).
- `ConceptEngine` persistido como nodos CONCEPT del World Model; dependencias
  conceptuales tipadas (requires/presupposes/generalizes/emerges_from/…), con
  **rechazo de circularidad** en relaciones acíclicas.
- Consultas: dependencias, "depende de este supuesto", generaliza, aplicabilidad,
  "dónde se rompe".
- Transformaciones conceptuales versionadas (no auto-marcadas como progreso).
- Compresión conceptual heurística y explicable.
- Conceptos de Codex quarantined como no verificados.

## Criterios de aceptación
Conceptos estructurados ✓; definiciones distinguidas ✓; regímenes de aplicabilidad ✓;
condiciones de ruptura ✓; dependencias ✓; transformaciones versionadas ✓; consultas
conceptuales ✓; ningún concepto aceptado solo por Codex ✓; pruebas de integridad/
persistencia ✓ (`tests/unit/test_cognitive_concepts.py`, 8 tests).

## Limitaciones
Sin ontología de conceptos importada; el benchmark usa conceptos conocidos (temperatura,
equilibrio) para validar la representación, no para descubrir.
