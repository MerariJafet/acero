# Estados epistemológicos y semáforo

## Tipos de objeto científico
ACERO representa el conocimiento con tipos explícitos (`epistemology/types.py`):

`OBSERVATION, MEASUREMENT, DATASET, CLAIM, EVIDENCE, COUNTEREVIDENCE, ASSUMPTION,
QUESTION, HYPOTHESIS, PREDICTION, MODEL, METHOD, EXPERIMENT, RESULT,
NEGATIVE_RESULT, ANOMALY, CONTRADICTION, INFERENCE, CONCLUSION, LIMITATION,
OPEN_QUESTION, RETRACTION, CORRECTION`.

## Estados del ciclo de vida
`DRAFT → PROPOSED → APPROVED → ACTIVE → TESTED → {SUPPORTED, WEAKENED, REFUTED,
INCONCLUSIVE} → ARCHIVED`. Las transiciones legales están en `STATE_TRANSITIONS`;
las ilegales se rechazan (`ledger.service.transition_state`).

## Semáforo epistemológico
El color de una afirmación **no** lo asigna el dicho de un modelo. Se **deriva
por reglas verificables** de su perfil de evidencia (`epistemology/traffic_light.py`):

| Color | Significado | Regla (resumen) |
|---|---|---|
| 🟢 GREEN | Fuerte, trazable, reproducido | procedencia + reproducido + sin contraevidencia pendiente |
| 🟡 YELLOW | Razonable pero incompleto | procedencia + evidencia, **no** replicado |
| 🟠 ORANGE | Hipótesis/inferencia exploratoria | contraevidencia ≥ apoyo, o base insuficiente |
| 🔴 RED | Especulación sin validación | sin evidencia o sin procedencia |
| ⚫ BLACK | Refutado/inválido/retractado/contaminado | flags de refutación |

La función `assess_color` es **total y determinista** (probado con
property-based testing en `tests/property/`). Esto evita que la "confianza" sea
un número inventado por un modelo.
