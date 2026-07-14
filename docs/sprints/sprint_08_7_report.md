# Sprint 8.7 — First Principles Engine · Reporte

**Estado:** ✅ Terminado

## Entregables
- **Análisis dimensional** (`cognitive/dimensions.py`): dimensiones SI, álgebra de
  cantidades, consistencia de ecuaciones, **Buckingham-Pi** (null space racional exacto).
  Declara que da escalamiento, no la constante.
- **Simetría→conservación** (Noether-inspirado, documentado como asociación, no prueba).
- **Motor de conservación**: un modelo declara qué conserva; verificación de requeridos.
- **Derivaciones verificables** (`ScientificDerivation`): pasos verificados por SymPy
  (identidades → 0); pasos no resueltos registrados; confianza acotada (<1); Codex no
  certifica.
- **Model search** por más que RMSE: parsimonia, generalización, restricciones;
  selecciona modelo mínimo, detecta modelos observacionalmente equivalentes y propone
  experimento distintivo (extrapolación).
- Clasificación de modelos: predicción ≠ explicación.

## Resultados (benchmarks)
Periodo del péndulo → 1 grupo Pi (período²·g/L, sin masa) ✓; ecuación inválida (F=mv)
rechazada ✓; energía cinética → 1 grupo ✓; derivación con paso erróneo detectada por
SymPy (confianza 0.5, paso no resuelto) ✓; múltiples modelos equivalentes → experimento
distintivo ✓.

## Criterios de aceptación
Análisis dimensional funcional ✓; grupos adimensionales ✓; ecuaciones inválidas
rechazadas ✓; restricciones ✓; simetrías/invariantes ✓; comparación más allá de RMSE ✓;
derivaciones verificables ✓; pasos no resueltos ✓; contraejemplos ✓; predicción vs
explicación ✓; Codex no certifica ✓. (`tests/unit/test_cognitive_first_principles.py`.)

## Limitaciones
Symbolic regression es enumeración ligera; optimización bayesiana/evolutiva son
interfaces. Buckingham-Pi no fija constantes numéricas (declarado).
