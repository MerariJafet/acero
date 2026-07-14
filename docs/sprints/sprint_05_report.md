# Sprint 5 — Motor de hipótesis y torneo de ideas · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-sprints-5-7-discovery-engine`

## Entregables
- `HypothesisCandidate` enriquecido (mecanismo, supuestos, predicciones,
  condiciones de falsación, variables/datos/herramientas requeridas, cómputo
  estimado, fuentes *reclamadas* sin verificar, novedad, riesgos, procedencia de
  generación con tokens) — `discovery/candidates.py`.
- Generación estructurada con Codex (`complete_json` + schema estricto) y un
  generador mock determinista diverso — `discovery/generation.py`.
- Diversidad por reglas + similitud léxica (sin embeddings): duplicados,
  paráfrasis, mecanismo compartido, cambios solo de parámetros, distintos; métricas
  (diversidad semántica/mecanismos/predicciones, cobertura de supuestos, número
  efectivo de hipótesis) — `discovery/diversity.py`.
- 10 tipos de hipótesis; toda investigación incluye null/baseline, mecanismo
  motivado, alternativa y modelo flexible.
- Falsifiability/actionability/specificity/assumption_burden por reglas —
  `discovery/falsifiability.py`.
- Torneo multiobjetivo + Elo con detalle completo de comparaciones — `tournament.py`.
- Registro de hipótesis rechazadas (motivo, evaluador, puntajes, `reconsider_if`),
  nunca eliminadas — `supervisor.py` + `store.py`.

## Criterios de aceptación
| Criterio | Evidencia |
|---|---|
| ≥8 hipótesis candidatas | mock genera 8; test `test_generates_at_least_8_and_a_null` |
| Duplicados/paráfrasis detectados | `test_duplicate_and_paraphrase_detection` |
| ≥4 mecanismos distintos | `test_at_least_four_mechanisms` |
| Cada hipótesis con condición de falsación | `test_every_candidate_has_a_falsification_condition` |
| Existe una hipótesis nula | idem (NULL/BASELINE presentes) |
| Torneo reproducible | `test_tournament_is_reproducible` |
| Ranking con procedencia | `test_ranking_provenance_recorded` (RANK/REJECT) |
| Descartadas permanecen | `test_rejected_candidates_cannot_be_deleted` |
| Codex no agrega citas sin verificar | `sources_verified=False`; test correspondiente |
| Pruebas deterministas + mock | 40+ tests unit/property |
| ≥1 ejecución real con Codex CLI | **Sí**: generó NULL/MATHEMATICAL/MECHANISTIC/COMPUTATIONAL, tokens registrados |

## Pruebas
`test_discovery_hypotheses.py` (10), `test_discovery_tournament.py` (6), más
property tests. Todos verdes.

## Limitaciones / deuda
- Los pesos del torneo recompensan hipótesis sin supuestos (baselines fuertes);
  configurable, con sensibilidad reportada.
- Diversidad léxica, no semántica (documentado; embeddings locales pendientes).
