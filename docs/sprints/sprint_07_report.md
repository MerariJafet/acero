# Sprint 7 — Motor de ejecución, búsqueda y aprendizaje · Reporte

**Estado:** ✅ Terminado

## Entregables
- **Árbol de investigación** persistente (Question→Hypotheses→Experiments) con
  estado, costo, prioridad, dependencia, resultado, ganancia de información,
  decisión, hijos y motivo de expansión/poda — `discovery/tree.py`. Estados:
  PROPOSED/VALIDATED/QUEUED/RUNNING/COMPLETED/FAILED/INCONCLUSIVE/PRUNED/CANCELLED/RETRYABLE.
- **Scheduler local**: concurrencia, timeout, reintentos, prioridad, cancelación,
  checkpoints (callback `on_state`), recuperación tras fallo, aislamiento de fallos
  parciales, resume por `skip_ids` — `discovery/scheduler.py`.
- **Búsqueda**: grid, random (semillado), adaptativa, poda explicable;
  interfaces para bayesiana/evolutiva/active learning — `discovery/search.py`.
- **Confidence update**: bayesiano cuando es válido, **ordinal etiquetado** cuando
  no; calidad del resultado modula el paso; nunca presenta confianza LLM como
  probabilidad calibrada — `discovery/confidence.py`.
- **Tool creation** controlado (screen → sandbox tests → benchmark → registry);
  herramienta no usable hasta aprobar; procedencia y versión registradas —
  `discovery/tool_creation.py`.
- **Negative Results Registry** consultable antes de repetir; nunca borra —
  `discovery/negative_registry.py`.
- **RecommendedNextExperiment** con ≥1 alternativa y `reason_not_to_run` —
  `discovery/next_experiment.py`.

## Criterios de aceptación
| Criterio | Evidencia |
|---|---|
| Árbol persistente | `test_tree_persists_and_survives_new_instance` |
| Varias ramas ejecutables | scheduler + benchmark (seeds) |
| Límites de recursos | `test_timeout_marks_task` |
| Fallos no destruyen estado | `test_partial_failure_isolated` |
| Reanudable | `test_resume_skips_completed` |
| Poda explicable | `test_tree_prune_is_explainable_and_recorded` |
| Confianza con trazabilidad | `test_confidence_updated_with_provenance` + evento CONFIDENCE_UPDATE |
| Ganancia de información observada | benchmark reporta EIG |
| Historial completo | provenance + store |
| Codex crea ≥1 herramienta pequeña | pipeline aprueba `gcd` (mock provider en test); Codex vía `complete_json` |
| Herramienta supera pruebas antes de usarse | `test_good_tool_is_approved`, quarantine tests |
| Siguiente experimento con explicación | `test_next_experiment_has_alternative` |

## Pruebas
`test_discovery_scheduler.py` (8), `test_discovery_tree_confidence.py` (10),
`test_tool_creation.py` (7, seguridad), property tests. Verdes.

## Limitaciones / deuda
- Cancelación de tareas es cooperativa (los sandboxes imponen timeout duro).
- Optimización bayesiana/evolutiva/active learning: interfaces, no implementadas.
- Tool creation con Codex real es lento (modelo de razonamiento); probado con mock
  + `complete_json` real disponible.
