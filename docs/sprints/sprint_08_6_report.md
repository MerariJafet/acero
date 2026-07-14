# Sprint 8.6 — Analogy Engine · Reporte

**Estado:** ✅ Terminado

## Entregables
- `ScientificAnalogy` + `SystemRepresentation` (forma estructural, roles de término,
  grupos adimensionales, invariantes/simetrías).
- Comparación estructural (sin embeddings): forma de la ecuación gobernante, mapeo de
  roles, correspondencia de grupos adimensionales, similitud superficial (peso 0.05).
- Scores separados; `deep_score` heurístico (2 dp, no calibrado).
- 7 pruebas de validación, incl. **transferencia predictiva verificada en el sandbox**
  (resonancia ω₀=√(c/a) medida en oscilador y RLC).
- Estados: STRUCTURALLY_SUPPORTED / VALID_IN_REGIME / PARTIALLY_VALID / MISLEADING /
  BROKEN / REJECTED; rechazadas/engañosas preservadas.
- Codex propone candidatos (`candidates.py`, arrays de pares) — ACERO valida, no acepta.

## Resultados (benchmark)
oscilador↔RLC **STRUCTURALLY_SUPPORTED** (transferencia de resonancia verificada),
difusión térmica↔partículas **VALID_IN_REGIME**, átomo↔sistema solar **MISLEADING**.
Ejecución real con Codex: propuso el mapeo completo (incluyendo términos de energía)
con predicciones de transferencia (condición subamortiguada R²<4L/C, factor Q).

## Criterios de aceptación
Analogías estructuradas ✓; superficial vs profunda ✓; relaciones/ecuaciones evaluadas ✓;
límites registrados ✓; engañosas detectadas ✓; predicciones transferidas ✓; ≥1
validación computacional (sandbox) ✓; Codex no decide ✓; rechazadas conservadas ✓;
explica por qué funciona o falla ✓. (`tests/unit/test_cognitive_analogies.py`,
`tests/science/test_cross_domain.py`.)

## Limitaciones
Formas estructurales y grupos adimensionales son de un catálogo (2º-orden ODE,
difusión); la detección no infiere formas arbitrarias todavía.
