# Sprint 4 — Ciclo mínimo de investigación computacional · Reporte

**Estado:** ✅ Terminado

## Flujo completo implementado
`experiment/orchestrator.run_pilot` ejecuta el ciclo entero y **no permite
saltos** de estado:

```
QUESTION_DEFINED → BACKGROUND_REVIEWED → ASSUMPTIONS_RECORDED →
HYPOTHESES_PROPOSED → PREDICTIONS_PREREGISTERED → EXPERIMENT_DESIGNED →
EXPERIMENT_APPROVED → RUNNING → RESULTS_CAPTURED → FALSIFICATION_REVIEW →
REPRODUCIBILITY_CHECK → HUMAN_REVIEW
```

## Experimento piloto
**Descubrimiento simbólico de una ley conocida (enfriamiento de Newton) desde
datos sintéticos con ruido.** La ecuación generadora se oculta al ajustador.

- **Ground truth:** `T(t) = T_env + (T0−T_env)·e^(−k·t)`, con `T_env=25, T0=90,
  k=0.7, ruido σ=1.5`.
- **Hipótesis competidoras (4):** lineal, cúbica, **exponencial físico**, y
  polinomio de grado 9 (flexible, propenso a sobreajuste).
- **Particiones:** train/val/test disjuntos en `[0,3]` + **extrapolación** en
  `(3,5]` (fuera del rango de entrenamiento).
- **Baseline ingenuo:** media de entrenamiento.
- **Multi-semilla:** seeds `[1,2,3]`.
- Ejecutado en el **sandbox** (numpy, red off, límites de recursos, timeout).

## Resultados (ejecución `seeds=1,2,3`)
| Métrica | Valor |
|---|---|
| Mejor modelo por RMSE de test | `exponential_physical` (2/3 semillas; cúbico 1/3) |
| k recuperado (media) | **0.6607** (real 0.7) |
| RMSE test (exponencial) | ~0.94 |
| RMSE extrapolación (exponencial) | ~1.50 |
| RMSE extrapolación (poly9) | **~24 614** (colapso por sobreajuste) |
| Baseline (media) | ~21.4 |

## Intento de refutación (Escéptico)
6 objeciones, comprobadas contra el registro de la ejecución: fuga de datos
(train/test disjuntos ✓), sobreajuste (poly9 falla), rango limitado
(extrapolación probada), baseline (reportado y superado), sensibilidad a semillas
(3 semillas ✓), y la objeción de fondo: **ajustar una forma funcional ≠ explicación
causal**. Con el set de semillas completo: 0 checks fallidos.

## Resultado negativo (preservado)
`poly9` sobreajusta: bajo error en train, catastrófico en extrapolación. Se
registra como `NEGATIVE_RESULT` y **no puede borrarse**.

## Reproducibilidad
Reejecución de la semilla 1 → hash del JSON de salida idéntico → `reproduced =
True`. Cada corrida guarda `manifest/environment/inputs/code/outputs/logs/
metrics/result/provenance/checksums`.

## Artefactos de aprendizaje (Tutor semilla)
`learning/`: intuition, mathematics, code_walkthrough, assumptions,
human_questions, knowledge_check.

## Lo que NO puede concluirse
- Que exista una ley nueva (se **recuperó una conocida**).
- Que el ajuste implique causalidad física.
- Que el resultado aplique fuera de estos datos sintéticos.

## Criterios de aceptación
Pregunta creada; ≥2 hipótesis competidoras con predicciones; plan previo a
ejecutar; sandbox ejecuta el script; código/parámetros/resultados guardados;
resultado reproducible; ≥1 intento de refutación; reporte con limitaciones; **no
se declara descubrimiento** — todos demostrados (10 tests en `tests/science/`).

## Pendientes / deuda
- Endurecer sandbox a Docker/nsjail para código no confiable (Sprint 7).
- Torneo de hipótesis y diseño experimental avanzado (Sprints 5–6).
