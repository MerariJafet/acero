# Sprint 8.9 — Experimentación activa, calibración y gate epistémico · Reporte

**Estado:** ✅ Terminado

## Entregables
- **Identificabilidad** (número de condición, correlación de parámetros, suficiencia de
  datos → IDENTIFIABLE/PARTIALLY/NON/DATA_INSUFFICIENT/REGIME_DEPENDENT); sin falsa
  precisión.
- **Diseño de experimento discriminante**: simula modelos competidores, elige la CI de
  máxima divergencia, estima EIG/costo/riesgo/modos de falla.
- **Loop activo** integrado con Discovery/scheduler/research-utility/World Model.
- **Calibración empírica**: reliability diagram, Brier, log loss, coverage, bootstrap;
  separa score heurístico / frecuencia empírica / probabilidad posterior / intervalo /
  confianza LLM (nunca mezclados).
- **Gate epistémico OBLIGATORIO** (14 reglas bloqueantes deterministas) con estados
  PASS/PASS_WITH_WARNINGS/BLOCKED/ESCALATE_TO_HUMAN; Codex advisory, promovido a bloqueo
  solo si nombra una regla.
- **Red-team**: variable espuria/omitida, leakage, ruido, no identificabilidad,
  equivalencia, no reproducibilidad → el gate bloquea.
- **Abstención explícita** ("no lo sé con los datos actuales") con razones.

## Resultados (benchmark)
L7 adversarial → **BLOCKED** con 8 bloqueadores. Calibración detecta sobre/subconfianza.
El loop propone la CI de mayor divergencia para modelos equivalentes.

## Dato real
SILSO manchas solares: período dominante **11.2 años**, clasificado **cuasiperiódico**,
**mínimo de Dalton (1809–1819)** detectado; se declara que el mecanismo del dínamo NO
puede inferirse.

## Criterios de aceptación
Detecta no identificabilidad ✓; diseña experimentos discriminantes ✓; ejecuta loop
activo ✓; actualiza modelos ✓; curvas de calibración ✓; separa scores de probabilidades
✓; gate bloquea errores críticos ✓; Codex no aprueba solo ✓; se abstiene ✓; registra por
qué no sabe ✓; pruebas adversariales ✓.

## Auditoría (Codex real, 8 hallazgos)
Correcciones verificables con regresión: se declara el caveat SINDy (derivadas del mismo
dato) y de biblioteca polinómica; coeficientes sin intervalos calibrados; método de
derivada en `imposed`.
