# ACERO — Reporte de causa raíz de EVA (salida plantillada)

**Síntoma observado (corrida de frontera del valle de radios):** las 6 hipótesis
rivales recibieron **la misma terna de vulnerabilidades** (`dependencia_fuente`,
`resultado_no_replicado`, `extrapolacion_injustificada`) y las preguntas salieron
genéricas: *«¿El efecto observado entre **la exposición** y **el outcome** se reproduce
en una fuente de raíz independiente?»*. EVA no razonó por hipótesis.

**Conclusión:** no es un bug aislado sino **tres defectos encadenados**. La ruta de EVA
del portal es **100 % determinista y estructural**; nunca llama a Codex; y el mapeo
hipótesis→ClaimRecord **descarta la semántica** de cada hipótesis, dejando idénticos los
únicos campos que EVA mira.

---

## Cadena de causa (con evidencia en código)

### Defecto 1 — El ClaimRecord llega vacío de contenido
`src/acero/portal/epistemic_bridge.py::_claim_from_hypothesis` (líneas 25-43) construye el
`ClaimRecord` con:

- `exposure_or_input=""`, `outcome_or_prediction=""` (¡vacíos!)
- `effect_direction` sólo si ya hay experimentos `supports` (no los había: EVA corrió
  **antes** de experimentar)
- `evidence_type=OBSERVATIONAL` **hardcodeado** para todas
- `provenance_roots` derivado sólo de experimentos `supports` → vacío para todas
- **NO** se pueblan `mechanism`, `assumptions`, `boundary_conditions`

Se pierden `argument`, `doubt`, `trigger_question`, `test_idea`, `competes_with`,
`discovery_angle`, `kind` — toda la riqueza que Codex sí generó por hipótesis.

### Defecto 2 — EVA es un scanner de reglas sobre esos campos
`epistemic_bridge` línea 64 llama `audit_external(c)` →
`src/acero/epistemic/eva.py::audit_external` (72-78) = `scan_vulnerabilities(claim)` +
`audit_assumptions(claim)`. `scan_vulnerabilities`
(`src/acero/epistemic/vulnerability.py`) es **determinista y conservador**, y sus reglas
condicionales dependen de los campos que quedaron vacíos:

| Vulnerabilidad | Condición de activación | ¿Disparó? |
|---|---|---|
| `.src` SINGLE_SOURCE | `n_independent_sources() ≤ 1` | ✅ (todas) |
| `.rep` NOT_REPLICATED | `replication ∈ {NONE, INTERNAL_ONLY}` | ✅ (todas) |
| `.ext` UNJUSTIFIED_EXTRAPOLATION | `not boundary_conditions` | ✅ (todas) |
| `.conf` CONFOUNDING | **requiere** `exposure_or_input AND outcome_or_prediction` | ❌ (campos vacíos) |
| `.rev` REVERSE_CAUSATION | idem | ❌ |
| `.mech` AMBIGUOUS_MECHANISM | `not mechanism AND effect_direction` | ❌ (ambos vacíos) |
| `.asm{i}` UNVALIDATED_ASSUMPTION | por cada `claim.assumptions` | ❌ (lista vacía) |

Resultado: **sólo las 3 incondicionales dispararon** → terna idéntica en las 6. La
**confusión** —el eje central de este caso científico— **nunca se evaluó** porque su
condición dependía de campos que el puente no pobló.

### Defecto 3 — Placeholders filtrados + sin Codex + sin trazabilidad
- `src/acero/questions/question_engine.py` líneas 133-134:
  `f"{claim.exposure_or_input or 'la exposición'} y {claim.outcome_or_prediction or 'el outcome'} se reproduce…"`
  → con campos vacíos, la pregunta usa los **placeholders** «la exposición / el outcome».
- Mismo patrón en `src/acero/epistemic/rival_theory_generator.py` líneas 21-22.
- `run_epistemic` **nunca recibe ni usa un provider LLM**: aunque el portal corría con
  `ACERO_LLM_PROVIDER=codex`, la ruta EVA/preguntas es enteramente determinista (la
  generación de hipótesis sí usó Codex, por otra ruta: `hypotheses.py`).
- No hay marca de procedencia (LLM vs heurística vs fallback) ni reducción de confianza.

### Factor agravante — Momento de ejecución
EVA corrió **antes** de los experimentos → `provenance_roots`, `replication_status` y
`effect_direction` estaban además uniformemente vacíos por falta de resultados, reforzando
la homogeneidad.

---

## Por qué importa
EVA plantillado **no cambia decisiones**: no señaló la confusión insolación↔[Fe/H], ni el
sesgo de selección por brillo (`sy_kepmag`), ni la dependencia de radios estelares —
justo las tres cosas que después *sí* mataron la señal en los experimentos. Un EVA
específico las habría anticipado y priorizado el placebo desde el diseño.

---

## Plan de corrección (Fase 1 de la directiva)

1. **Enriquecer el ClaimRecord** (`_claim_from_hypothesis`): poblar `exposure_or_input`,
   `outcome_or_prediction`, `effect_direction`, `mechanism`, `assumptions`,
   `boundary_conditions` desde los campos reales de la hipótesis. Esto **activa** las
   vulnerabilidades condicionales y **de-genericiza** preguntas y rivales, sin tocar el
   scanner.
2. **Razonamiento por hipótesis con Codex** (modo LLM inyectable): extraer supuestos
   concretos, mecanismo y modos de fallo por claim; **fallback determinista** si no hay
   provider; **marcar procedencia** (`llm`/`heuristic`/`fallback`) y **bajar confianza**
   en fallback. Cada vulnerabilidad debe citar supuesto + evidencia a favor/en contra +
   modo de fallo.
3. **De-duplicación semántica**: prohibir terna idéntica entre dos claims sin
   justificación explícita; marcar solapamiento.
4. **Preguntas trazables**: cada pregunta rastreable a una vulnerabilidad concreta y con
   «qué creencia cambiaría» y «qué resultado sería discriminante».
5. **Cablear el provider** desde el portal a `run_epistemic`.

**Criterio de salida:** EVA produce críticas no redundantes, trazables, específicas y
accionables; cada pregunta se rastrea a una vulnerabilidad real; y el benchmark paralelo
(heurístico vs LLM-específico) muestra mayor especificidad por claim, menor duplicación
semántica y cambios reales en el diseño experimental — no sólo más texto.

**Veredicto de esta fase (parcial):** `EVA_CORREGIDO_LISTO_PARA_BENCHMARK` **aún no**;
causa raíz identificada y corrección especificada. Siguiente: implementar y probar.
