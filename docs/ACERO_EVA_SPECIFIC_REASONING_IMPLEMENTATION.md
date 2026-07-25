# ACERO — Implementación de EVA específico por hipótesis (Fase 1)

Corrige la causa raíz descrita en `ACERO_EVA_ROOT_CAUSE_REPORT.md`: EVA ya no produce una
terna de vulnerabilidades plantillada ni preguntas genéricas. Cada hipótesis se reconstruye
con su propia semántica y su procedencia queda trazada.

## Qué cambió

### 1. Reconstrucción semántica por hipótesis (`src/acero/portal/epistemic_bridge.py`)
- `_claim_from_hypothesis(h, exps, *, extractor=None)` ahora **enriquece** el `ClaimRecord`
  con `mechanism`, `assumptions`, `boundary_conditions`, `population/exposure/outcome`
  provenientes de los campos reales de la hipótesis (argument, doubt, competes_with,
  trigger_question, test_idea) — no sólo el título.
- `heuristic_extract(h)`: extractor **determinista** por defecto. Como cada hipótesis trae
  argumento/duda/rivales distintos, las vulnerabilidades resultantes son **específicas por
  claim** (p. ej. `supuesto_no_validado` con texto propio), en lugar de un molde común.
- **Costura LLM inyectable** (`Extractor = Callable[[hyp], (fields, provenance)]`): el portal
  puede pasar un extractor Codex por hipótesis; los tests inyectan uno falso y quedan
  offline. Un extractor que falla **degrada a fallback**, nunca rompe.

### 2. Trazabilidad de procedencia y confianza
Cada claim reporta `provenance ∈ {llm, heuristic, fallback}` y `confidence`
(`llm`=1.0, `heuristic`=0.7, `fallback`=0.5). Expuesto en `reasoning` del JSON del endpoint.

### 3. De-duplicación semántica
`run_epistemic` compara el **conjunto de tipos de vulnerabilidad** por claim y marca en
`duplicate_groups` (y en `reasoning[cid].duplicate_with`) cualquier par que reciba una
firma idéntica — el modo de fallo exacto de la corrida anterior.

### 4. Preguntas no genéricas (`src/acero/questions/question_engine.py`)
La plantilla de transportabilidad ya no cae a los placeholders «la exposición / el
outcome»: cuando faltan exposición/outcome, referencia el **texto real del claim**.

## Verificación

- **Unit tests** (`tests/unit/test_epistemic_bridge_specific.py`, 6 casos): claims distintos
  → vulnerabilidades distintas; enriquecido > terna genérica; procedencia/confianza
  (heuristic/llm/fallback); pregunta de transportabilidad referencia el claim, no el
  placeholder; con exposición/outcome conocidos usa las variables reales.
- **Demostración en vivo** (mismo proyecto del valle de radios, código nuevo):
  - Antes: 6 claims con terna idéntica `{dependencia_fuente, resultado_no_replicado, extrapolacion_injustificada}`; preguntas con «la exposición / el outcome».
  - Después: `duplicate_groups=[]`; H0 = `{dependencia_fuente, extrapolacion, resultado_no_replicado, supuesto_no_validado}` vs H5 = `{dependencia_fuente, resultado_no_replicado, supuesto_no_validado}` (difieren); 3 supuestos con texto propio por claim; procedencia `heuristic` conf 0.7; pregunta = «¿La relación afirmada en «El valle se desplaza con [Fe/H]…» se reproduce en una fuente de raíz independiente?».

## Pendiente (siguientes commits de la Fase 1)
- Extractor **Codex real** por hipótesis (poblar exposure/outcome → activa la vulnerabilidad
  de **confusión**, central en este caso) cableado desde el portal, con la costura ya lista.
- `ACERO_EVA_QUESTION_ENGINE_BENCHMARK.md`: comparar heurístico anterior vs LLM-específico
  con métricas de especificidad, duplicación semántica, vulnerabilidades reales/falsas,
  poder discriminante y **cambios reales en el diseño experimental** — un módulo no mejora
  por generar más texto.

**Veredicto de fase:** `EVA_CORREGIDO_LISTO_PARA_BENCHMARK` (ruta heurística específica y
trazable lista; falta cablear el extractor Codex y correr el benchmark comparativo).
