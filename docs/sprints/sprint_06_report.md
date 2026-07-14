# Sprint 6 — Diseño experimental y ganancia de información · Reporte

**Estado:** ✅ Terminado

## Entregables
- `ExperimentProposal` completo (variables independientes/dependientes/controladas,
  espacio de parámetros, baseline, controles ±, métricas, predicciones
  prerregistradas, reglas de falsación/detención, presupuesto, EIG esperado,
  riesgos, supuestos) — `discovery/experiment_design.py`.
- **Matriz de discriminación** Experiment × Hypothesis × Expected-Outcome;
  rechazo de experimentos no discriminantes; grupos con ambigüedad parcial
  surfaced.
- **Expected Information Gain** bayesiano (`EIG = H(prior) − E[H(posterior)]`) +
  heurística documentada + **sensibilidad a priors** — `discovery/information_gain.py`.
- **Research utility** multiobjetivo transparente (componentes, pesos, benefit,
  cost, sensibilidad a pesos), sin colapsar a un número opaco — `research_utility.py`.
- Diseño estadístico: baseline, controles ±, train/val/test, extrapolación,
  múltiples semillas, ruido, detección de leakage (train/test disjuntos).
- **Stopping rules** con decisión explícita CONTINUE/REFINE/PAUSE/STOP/
  ESCALATE_TO_HUMAN — `discovery/stopping.py`.
- Crítico por reglas (**barrera obligatoria**) + crítico Codex (**advisory**) —
  `discovery/experiment_critic.py`.

## Criterios de aceptación
| Criterio | Evidencia |
|---|---|
| Cada hipótesis priorizada → ≥1 experimento | benchmark + `experiment propose` |
| Matriz de resultados esperados | `DiscriminationMatrix` |
| Se rechazan experimentos no discriminantes | `test_non_discriminating_rejected` |
| EIG o heurística documentada | `test_bayesian_eig_*`, `test_heuristic_eig_documented` |
| Sensibilidad a priors y pesos | `test_prior_sensitivity_reports_range`, `test_weight_sensitivity_detects_instability` |
| Todo experimento con controles | crítico bloquea si faltan (`test_rule_critic_blocks_missing_controls`) |
| Stopping rules | `test_stopping_rules_decisions` |
| Crítico por reglas y por Codex | `test_rule_critic_passes_valid`, `test_codex_critic_is_advisory_never_blocking` |
| Experimentos rechazados registrados | store `proposal`/negativos |
| No ejecución sin prerregistro | `require_discriminating` + crítico |

## Pruebas
`test_discovery_experiment.py` (16), todas verdes.

## Limitaciones / deuda
- EIG con probabilidades explícitas simples; calibración real → Sprint 11.
- Unidades de costo son heurísticas normalizadas [0,1], no monetarias (documentado).
