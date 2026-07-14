# Sprint 8.8 — Governing Structure Inference · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-governing-structure-inference`

## Entregables
- Estimación de derivadas (diferencias finitas, Savitzky–Golay, spline) con método,
  error y regiones no confiables.
- Relevancia de variables (redundancia, casi-constantes; "predictivo ≠ causal").
- Biblioteca de términos con filtrado por dominio (1/x en cruces por cero, log/sqrt de
  no positivos), duplicados algebraicos, forbidden, complejidad; registra por qué se
  incluye cada término.
- **Identificación dispersa STLSQ** (ridge para colinealidad) + selección de
  estabilidad (thresholds × bootstrap) + sensibilidad al threshold.
- **Regresión simbólica** con propuestas de Codex validadas (SymPy parse + finito).
- **Descubrimiento de invariantes** (direcciones de baja varianza; exact/approx/artifact;
  robustez a ruido).
- **Detección de regímenes** por homogeneidad de residuales del modelo global (robusta a
  datos periódicos).
- **Equivalencia de modelos** (algebraica, observacional, divergencia fuera de muestra).

## Recuperación (datos limpios, ecuación oculta)
exponencial, logístico (0.8x−0.08x²), armónico (v; −4x), amortiguado (−4x−0.5v),
depredador-presa (1.1x−0.4xy; −0.4y+0.1xy) — todos recuperados. Bajo ruido, R² degrada
suavemente; con variable omitida, residuales estructurados (autocorr≈1.0) → variable
faltante señalada, no inventada.

## Criterios de aceptación
Infiere ODE sencilla ✓; bibliotecas respetan dominio ✓; recupera términos con ruido
moderado ✓; sensibilidad a hiperparámetros ✓; modelos equivalentes detectados ✓; ≥1
invariante ✓; cambio de régimen en benchmark ✓; no confunde ajuste con mecanismo
(nivel declarado) ✓; alternativas conservadas ✓; Codex no es evidencia ✓; pruebas de
regresión ✓.

## Limitaciones
Biblioteca polinómica (dinámicas no polinómicas requieren ampliarla — Codex propuso
abs(v)·v y sign(v)); coeficientes sin intervalos calibrados; derivadas del mismo dato
que la regresión (limitación intrínseca de SINDy).
