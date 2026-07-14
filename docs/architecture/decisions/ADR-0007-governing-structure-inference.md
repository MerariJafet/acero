# ADR-0007: Inferencia de estructura gobernante con gate epistémico obligatorio

- **Estado:** Aceptado
- **Fecha:** 2026-07-13

## Contexto
Los Sprints 8.8–8.9 exigen inferir ESTRUCTURA (no ajustar curvas) desde datos, y evitar
que ACERO elija una estructura solo porque ajusta mejor. Debe distinguir niveles
(fitting ≠ identificación ≠ descubrimiento ≠ causalidad) y bloquear conclusiones
defectuosas.

## Decisión
Paquete `src/acero/inference/` con: estimación de derivadas multi-estrategia, biblioteca
de términos filtrada, **STLSQ con ridge** (SINDy-inspirado) + estabilidad, invariantes,
regímenes (por residual del modelo global), identificabilidad, equivalencia, diseño de
experimento discriminante, calibración empírica, y un **gate epistémico OBLIGATORIO** de
14 reglas deterministas. Codex propone términos/audita, pero nunca es evidencia ni
aprueba por sí solo. El motor declara su nivel y se abstiene cuando corresponde.

## Alternativas descartadas
- Elegir el modelo de menor RMSE (rechazado: es ajuste, no identificación).
- Aceptar términos/derivaciones de Codex sin verificación (rechazado por la constitución).
- Copiar una implementación académica de SINDy sin revisar licencia (se implementó una
  versión auditable propia).

## Consecuencias
- (+) Recupera 5 sistemas clásicos con la ecuación oculta; detecta variable omitida,
  régimen, invariante; bloquea el caso adversarial; se abstiene.
- (+) Dato real (manchas solares): período de 11.2 años + mínimo de Dalton, con
  honestidad sobre el mecanismo.
- (−) Biblioteca polinómica (no infiere formas arbitrarias); coeficientes sin intervalos
  calibrados; derivadas del mismo dato (limitación intrínseca de SINDy) — todo declarado.
