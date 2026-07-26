# ACERO — Decisión go/no-go de confirmación (valle de radios vs [Fe/H])

**Condición de entrada a la ruta confirmatoria** (directiva): sólo si el re-análisis
alcanza `RESULTADO_EXPLORATORIO_ROBUSTO`.

## Decisión: **NO-GO** — `NO_APTO_PARA_CONFIRMACION`

El re-análisis corregido (muestra real de 2770–3894 planetas, placebo de detectabilidad
corrido, discriminador de mecanismo probado) **no** alcanzó exploratorio robusto para la
afirmación positiva. Al contrario: aportó **evidencia robusta en contra** del efecto que se
buscaba.

### Evidencia que fuerza el NO-GO
- El coeficiente de [Fe/H] **se contrae 59 %** al controlar detectabilidad; CI95 cruza cero.
- El discriminador fotoevaporación vs core-powered (cambio de signo con periodo) está
  **refutado**: p≈0.19, |β| < null95, cambio de signo no estable, placebo de brillo lo iguala.
- La 2ª implementación **discrepó** (sin reproducción por implementación independiente).

### Consecuencias (reglas respetadas)
- **NO se preregistra** ninguna hipótesis confirmatoria (prohibido con resultado no robusto).
- **NO se descarga ni inspecciona CKS/TESS** como fuente confirmatoria (prohibido antes de
  exploratorio robusto + protocolo congelado). Independencia sigue en **Nivel 1**.
- El **resultado negativo se conserva** y se documenta (`ACERO_FRONTIER_REANALYSIS_DOSSIER.md`).

### Qué haría falta para reabrir la ruta (no ahora)
1. Una observable que separe los mecanismos **sin** depender del signo-con-periodo (p.ej.
   densidad/composición inferida, o dependencia con masa estelar) que **sí** supere placebo
   y nulo de forma estable.
2. Reproducción por una **segunda implementación** que concuerde.
3. Sólo entonces: congelar protocolo (con placebo `kepmag` obligatorio y tamaño mínimo
   preregistrado) y recién ahí evaluar una fuente de raíz independiente.

**Veredicto final de esta iteración:** `NO_APTO_PARA_CONFIRMACION` +
`RESULTADO_INCONCLUSO` para el positivo, con evidencia robusta de que el efecto buscado es
en buena parte **detectabilidad/selección**, no composición. El techo sigue siendo la
revisión humana; nada es un descubrimiento.
