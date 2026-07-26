# ACERO — Dossier del re-análisis exploratorio (valle de radios vs [Fe/H])

**Re-corrida corregida** tras arreglar EVA (razonamiento por hipótesis) y el codegen
(cross-match consciente de esquema). Régimen: **exploratorio**, exposición previa
registrada (anti-HARKing). Proyecto `proj_01KYDVD6HTJXEQD3RS56DB7WEP`.

> **Veredicto: `NO_APTO_PARA_CONFIRMACION`** — el positivo NO se estableció y hay
> **evidencia robusta EN CONTRA** del discriminador de mecanismo. Estado: sigue en
> `EVIDENCIA_PRELIMINAR`. No se abre CKS. El resultado negativo se conserva.

---

## Lo que cambió respecto a la primera corrida (el fix funcionó)

| | 1ª corrida | Re-corrida |
|---|---|---|
| Estrategia de datos | join externo a `stellarhosts` | **una sola tabla, sin join** (fix) |
| Muestra usable | **3 planetas** | **2248–3894 planetas** |
| Placebo `kepmag` | tardío/parcial | **corrido en todos los diseños** |
| Discriminador de mecanismo | no probado limpio | **probado y refutado** |

El único experimento que aún intentó el join obtuvo `rows_matched=0` y **el guardarraíl
lo detectó** y cayó a la tabla base (3130 planetas) — el defecto ya no pasa silencioso.

## Resultados con datos reales (9 experimentos)

**H0 — ¿la señal [Fe/H] es detectabilidad, no composición?**
- Modelo jerárquico (n=2770): el coeficiente de [Fe/H] **se contrae 59 %** al añadir
  proxies de detectabilidad Kepler + covariables estelares
  (`absolute_beta_drop_fraction_from_stellar_to_full=0.59`); CI95 del modelo completo
  **[−0.179, +0.500] cruza cero**. → la señal se **disuelve** bajo control de
  detectabilidad. Cross-check discrepó (supports vs inconclusive) → **degradado por ACERO**.
- Bootstrap vs placebo `sy_kepmag`: control positivo interno insuficiente → inconclusive.

**H4 — ¿el gradiente [Fe/H] cambia de signo con el periodo? (fotoevaporación vs core-powered)**
- **REFUTADO** en múltiples diseños: interacción z=1.04, permutación **p=0.19**;
  |β(FeH×logP)|=0.069 < null95=0.104; cambio de signo **no estable**
  (`bootstrap_sign_change_rate=0.57` ≈ volado de moneda); el **placebo `kepmag`
  (interacción 2.84) supera** a la señal real; la interacción held-out no superó el nulo.

## Análisis de sensibilidad
El signo/magnitud del efecto de [Fe/H] **no es estable**: depende de si se incluye o no el
control de detectabilidad (β cae 59 %), y la interacción con periodo es indistinguible del
nulo de permutación agrupado por estrella. Dos verificaciones cruzadas **discreparon**
(supports vs inconclusive/refutes) → inestabilidad de implementación persistente.

## Críticas no resueltas
- La segunda implementación siguió discrepando en H0 (supports vs inconclusive) → ACERO
  degradó el resultado en lugar de contarlo. No hay reproducción por implementación
  independiente.
- La misión H0 quedó con `rigor_loop` en heartbeat stale (el panel adversarial no cerró);
  hallazgo menor de robustez del mission engine (no afecta los experimentos, que sí
  completaron). Se documenta, no se oculta.

## Criterios de RESULTADO_EXPLORATORIO_ROBUSTO — evaluación
| Criterio | ¿Cumple? |
|---|---|
| la señal supera el placebo | ❌ (placebo `kepmag` la iguala/supera) |
| dirección/magnitud estables en sensibilidad | ❌ (β cae 59 % con controles) |
| 2ª implementación compatible | ❌ (cross-check discrepó) |
| no depende de un único preprocesamiento | ❌ (depende del control de detectabilidad) |
| cobertura del cross-match suficiente | ✅ (2770–3894) |
| predicción que discrimina ≥2 rivales | ✅ probada — **refutada** |
| panel adversarial sin bloqueos duros | ⚠️ (rigor H0 no cerró) |

**5 de 7 en contra del positivo.** No hay resultado exploratorio robusto para la
afirmación positiva; sí hay evidencia robusta de que el discriminador de mecanismo (cambio
de signo con periodo) **no se sostiene** y de que la señal [Fe/H] es en buena parte
**detectabilidad/selección**, no composición.

## Afirmación máxima permitida
> «Sobre 2770–3894 planetas Kepler DR25 (una sola tabla, sin cross-match defectuoso), el
> efecto de [Fe/H] en la posición del valle **se contrae ~59 %** al controlar
> detectabilidad y covariables estelares y su CI95 cruza cero; el cambio de signo con el
> periodo que distinguiría fotoevaporación de core-powered **no supera el nulo de
> permutación (p≈0.19)** ni un placebo de brillo. Los datos **no establecen** una firma de
> metalicidad que distinga mecanismos.»

Prohibido: «distingue mecanismos», «confirmado», «causa».

## Qué aprendió ACERO
1. **De su proceso:** un `join_hint` que premiaba unir por nombre convirtió una muestra de
   4083 en 3 — un defecto de integración disfrazado de límite científico. El guardarraíl de
   cobertura y la preferencia por columnas in-table lo previenen.
2. **De los datos:** con muestra real el efecto de [Fe/H] es débil y confundido con
   detectabilidad Kepler; el placebo de brillo era la vulnerabilidad correcta a priorizar
   (que el EVA plantillado NO señaló, y el EVA específico sí encuadra).
3. **De la hipótesis:** el discriminador fotoevaporación/core-powered vía signo-con-periodo
   no es medible con esta muestra/precisión; se necesita otra observable.
