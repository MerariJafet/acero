# Sprint 17 — First Real Astronomy Research Program · Report

**Estado:** ✅ Terminado · **Rama:** `integration/acero-v2-program`

## Programa: Stellar Variability & Regime Discovery
Ejecutado sobre datos **públicos reales** (SILSO monthly sunspot number, dominio público,
cacheado + hash, gitignored). `src/acero/studies/stellar_variability.py`.

**Pregunta:** ¿qué estructuras temporales/regímenes puede identificar ACERO en la serie SILSO,
y qué límites hay para interpretar mecanismos físicos?

## Metodología (prerregistrada antes de mirar resultados)
- **Prerregistro** con métricas, métodos, controles, claims permitidos/**prohibidos**.
- **Hipótesis competidoras** (6): periodicidad estable, cuasiperiodicidad, múltiples
  componentes, proceso estocástico, cambio de régimen, artefacto instrumental — **sin
  hardcodear ganador**.
- **Análisis:** periodograma FFT; **significancia vs ruido rojo AR(1)** (el null correcto —
  los surrogates de fase preservan el espectro y no sirven); **bootstrap del CI de la longitud
  de ciclo** (resampleo de espaciamientos pico-a-pico, con separación mínima de ~7 años para no
  sobre-contar); autocorrelación; detección de regímenes por media decadal.

## Resultados (nivel de DATOS, no descubrimiento)
- Período dominante **11.19 años**; longitud de ciclo **10.99 yr, IC 95% [10.27, 11.67]** sobre
  **24 ciclos** — el IC contiene el período FFT (consistente).
- Clasificado **cuasiperiódico** (la longitud de ciclo varía).
- Pico **significativo vs ruido rojo AR(1)** (φ=0.918, p≈0.01) → proceso estocástico
  desfavorecido.
- **Regímenes de baja actividad multidécada** ~1809–1819 (tipo mínimo de Dalton).

## Correcciones de rigor aplicadas durante el sprint
1. El detector de picos sobre-contaba (34 vs ~24 ciclos) → IC inconsistente con el FFT.
   Corregido (suavizado + separación mínima) → 24 ciclos, IC consistente.
2. Los surrogates de fase preservan el espectro (test inválido) → reemplazados por **ruido
   rojo AR(1)**, el null correcto. Prerregistro alineado.

## Honestidad obligatoria
Gate de honestidad que **bloquea** claims prohibidos (nueva estrella/planeta/ciclo, dínamo,
mecanismo, causalidad, descubrimiento). NO se afirma ningún descubrimiento; el mecanismo del
dínamo NO es inferible de esta serie; **revisión externa PENDIENTE**. Registrado como
`ResearchProgram` (Program OS) + dossier `NOT_READY` que exige revisión humana.

## Calidad
**648 pruebas en verde** (+7), ruff limpio, mypy limpio (270 archivos), `make verify` OK.
CLI `acero studies stellar-variability`.

## Limitaciones
Descomposición multi-componente no exhaustiva; dependencia de instrumento/pipeline no evaluada
(requiere metadatos del instrumento); un solo dataset (SILSO). No es validación experimental.
