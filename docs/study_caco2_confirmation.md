# Estudio 1 — Régimen de confirmación sobre datos reales (Caco-2 / TDC)

Primer uso EN VIVO de la Constitución Científica Computable con separación real
descubrimiento→confirmación. Es una **validación de método** (recupera una relación
farmacológica conocida), no un descubrimiento — el primer estudio que el revisor externo
recomendó ("recuperar un fenómeno real / negativo robusto").

## Pregunta
¿La polaridad molecular (capacidad de puente-H, proxy de TPSA por conteo de O+N en el
SMILES) predice una **menor permeabilidad Caco-2**? (Relación conocida: regla de Veber.)

## Diseño (dos regímenes, por código)
1. **Datos reales:** `caco2_wang` de Therapeutics Data Commons (Harvard Dataverse) vía el
   resolver de ACERO + descarga confiable con hash. **910 moléculas**, SMILES + logPapp
   medido, sha256 `447d9f1af487…`.
2. **Split determinista** (hash, sal `caco2-2026`): descubrimiento **619** / holdout
   **291** (sellado).
3. **Régimen A — descubrimiento** (libre) sobre las 619: corte por mediana de polaridad,
   t de dos muestras.
4. **Protocolo CONGELADO** (`FrozenAnalysisPlan` → hash `sha256:8247382f…`) con hipótesis,
   variable primaria, población, transformación, modelo, prueba, regla de decisión
   (`|t|>1.96 y efecto>0`) y condiciones de fracaso — **antes** de tocar el holdout.
5. **Holdout abierto** solo tras congelar (gated por `HoldoutManager`); se registra el
   `UnblindingEvent` → el régimen pasa a `confirmation`.
6. **Confirmación:** el MISMO análisis sobre las 291 retenidas, evaluado con la regla
   **congelada** (no post-hoc).

## Resultado real
| Fase | Efecto (baja−alta polaridad) | t | Detectado |
|---|---:|---:|:--:|
| Descubrimiento (n=619) | +0.746 logPapp | 13.10 | sí |
| **Confirmación holdout (n=291)** | **+0.769 logPapp** | **9.53** | **sí** |

- **Veredicto (regla congelada):** predicción confirmada — mayor polaridad → menor
  permeabilidad, misma dirección y magnitud en el holdout.
- **Estado ACERO alcanzado:** `CONFIRMADO_EN_HOLDOUT`.
- **Deuda de exploración:** ninguna (1 comparación efectiva; una sola prueba primaria
  pre-registrada).

## Honestidad
- Es **validación de método**, no un descubrimiento: la relación TPSA↔permeabilidad es
  conocida. Sirve para demostrar que la maquinaria de confirmación funciona sobre datos
  reales y que ACERO **no infla** un resultado exploratorio a "confirmado" sin holdout.
- El holdout es un **split del mismo dataset**, así que el estado se detiene en
  `CONFIRMADO_EN_HOLDOUT`; NO se reclama `REPLICADO_EN_DATASET_INDEPENDIENTE` (eso exigiría
  otra cohorte, p. ej. PAMPA o un Caco-2 de otro laboratorio).
- El techo sigue siendo la revisión humana.

## Reproducible
Script: `scripts/study_caco2_confirmation.py` (descarga real; correr con red).

## Panel adversarial plural EN VIVO (8 voces vía Codex)

Corrido sobre el resultado del estudio. Cada persona en su mandato, **desacuerdo
preservado**:

| Voz | Veredicto | Objeción clave |
|---|---|---|
| Estadístico | prometedor | dicotomizar por mediana pierde info; sin ajuste por covariables |
| **Causalista** | **defectuoso [BLOQUEA]** | estimando asociacional; confusión no controlada (peso molecular, lipofilia, clase química) |
| Experto de dominio | prometedor | O+N es proxy crudo de TPSA (ignora carga, donadores/aceptores, zwitteriones) |
| Replicador | prometedor | reproduce el contraste pero con el mismo pipeline/corte |
| Detective de datos | prometedor | sin auditoría de duplicados/sales/tautómeros → posible fuga entre splits |
| Revisor de novedad | prometedor | NO novedoso: recapitula TPSA / Veber-Lipinski |
| Abogado del mecanismo alt. | prometedor | modelos rivales: tamaño molecular; lipofilia (logD) |
| Redactor hostil | prometedor | el abstract debe ser asociativo, no causal ni universal |

**Agregado:** en disputa · desacuerdo=2 · peor veredicto=defectuoso · **bloqueado por el
causalista (mandato duro)**.

El panel es más exigente que el crítico único: cazó la confusión (peso molecular/lipofilia),
la no-novedad, la posible fuga por sales/tautómeros, y **bloqueó el lenguaje causal** — que
es exactamente la disciplina que pedía el revisor externo.
