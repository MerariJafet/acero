# Sprint 2 — Expediente científico y modelo de conocimiento · Reporte

**Estado:** ✅ Terminado

## Entregables
- **Entidades epistémicas** (Pydantic v2, `epistemology/schemas.py`):
  ResearchProject, ResearchQuestion, Assumption, Hypothesis, Prediction,
  ExperimentPlan, ExecutionRun, Evidence, CounterEvidence, ResearchResult,
  NegativeResult, ScientificClaim, OpenQuestion, DecisionRecord, ProvenanceEvent,
  ConfidenceAssessment, SourceDocument, SourceFragment.
- **Tipos y estados** (`types.py`): 24 tipos epistémicos; máquina de estados con
  transiciones legales; **semáforo epistemológico** por reglas (`traffic_light.py`).
- **Persistencia** (SQLAlchemy 2.0, `ledger/models.py` + `db.py`): SQLite por
  defecto; tabla genérica `entities` + relacionales para runs/provenance/etc.;
  **historial de versiones** por entidad.
- **ResearchLedger** (`ledger/service.py`): CRUD con **reglas de integridad**,
  transiciones validadas, procedencia append-only.
- **Exportación** (`ledger/export.py` + `acero project export`): dossier
  JSON + Markdown + manifest + checksums (SHA-256).
- **Esquemas JSON** exportados (`scripts/export_schemas.py` → `schemas/*.json`).

## Reglas de integridad (todas probadas)
| Regla | Prueba |
|---|---|
| Hipótesis pertenece a una pregunta existente | `test_hypothesis_requires_existing_question` |
| Predicción pertenece a una hipótesis existente | `test_prediction_requires_existing_hypothesis` |
| Resultado pertenece a una ejecución existente | `test_result_requires_run` |
| Afirmación con evidencia o marcada especulación | `test_claim_requires_support_or_speculation_flag` |
| Evidencia/contraevidencia con procedencia | `test_evidence_requires_provenance` |
| Resultado negativo no se borra en silencio | `test_negative_result_cannot_be_deleted` |
| Transiciones de estado ilegales rechazadas | `test_illegal_state_transition_rejected` |
| Cada cambio crea historial + procedencia | `test_history_and_provenance_recorded` |
| Edición de hipótesis post-resultado se marca | `test_harking_guard_flags_post_result_hypothesis_edit` |

## Criterios de aceptación
Crear proyecto/pregunta/hipótesis, asociar evidencia y contraevidencia, sin
resultados huérfanos, trazabilidad por cambio, export completo, reglas con
pruebas — **todos demostrados** (11 tests de ledger + 2 de export).

## Pendientes / deuda
- Índices/consultas relacionales más ricas (grafo llega en Sprint 8).
- pgvector cuando se active recuperación semántica.
