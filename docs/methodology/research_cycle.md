# El ciclo de investigación de ACERO

ACERO convierte curiosidad en conocimiento verificable mediante un ciclo
explícito y auditable. La máquina de estados vive en
`experiment/workflow.py` y **no permite saltos**.

```
QUESTION_DEFINED
  → BACKGROUND_REVIEWED
    → ASSUMPTIONS_RECORDED
      → HYPOTHESES_PROPOSED        (≥2 hipótesis competidoras)
        → PREDICTIONS_PREREGISTERED (predicciones fijadas antes de ejecutar)
          → EXPERIMENT_DESIGNED
            → EXPERIMENT_APPROVED   (decisión humana registrada)
              → RUNNING             (sandbox, multi-semilla)
                → RESULTS_CAPTURED
                  → FALSIFICATION_REVIEW  (el Escéptico intenta refutar)
                    → REPRODUCIBILITY_CHECK (reejecución + comparación de hash)
                      → HUMAN_REVIEW
                        → CLOSED
```

## Qué garantiza cada etapa
- **Prerregistro antes de ejecutar.** Impide HARKing y p-hacking: predicciones y
  criterios de éxito se hashean antes de ver resultados (`prereg.py`).
- **Hipótesis competidoras.** Se exige más de una explicación; el ganador se
  elige por desempeño fuera de muestra, no por narrativa.
- **Refutación.** El Escéptico plantea objeciones estándar (fuga de datos,
  sobreajuste, rango limitado, baseline, semillas, ajuste≠explicación) y las
  comprueba contra el registro de la ejecución.
- **Reproducibilidad.** Cada corrida guarda entorno, semillas y hashes; se
  reejecuta para confirmar que produce el mismo resultado.
- **Revisión humana.** El humano cierra el ciclo. ACERO nunca declara
  descubrimiento ni autoría.

## Principio rector
Optimizar reducción de incertidumbre, calidad de evidencia, reproducibilidad,
falsabilidad, diversidad de hipótesis y **aprendizaje humano** — no la cantidad de
resultados. La heurística de utilidad de investigación
(`ResearchUtility`) es configurable y auditable, no una verdad científica.
