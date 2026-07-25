# EVA + Motor de Preguntas Científicas — de responder a PREGUNTAR

Respuesta (lean) al dictamen que pide que ACERO no solo ejecute hipótesis, sino que
**recorra la cadena**: comprender una afirmación → reconstruir su evidencia → hallar dónde
podría fallar → convertir esa vulnerabilidad en una pregunta → formular rivales → diseñar
una prueba que los distinga. Todo aditivo, integrado con la Constitución, sin romper nada.

## Módulos

| Paquete/módulo | Qué hace |
|---|---|
| `epistemic/claim_reconstructor.py` | `ClaimRecord`: reconstruye qué afirma una teoría (población, exposición, outcome, evidencia, supuestos, replicación, límites, raíces de procedencia). **Comprender antes de criticar.** |
| `epistemic/vulnerability.py` (**EVA**) | `EpistemicVulnerability` estructurada + 20 tipos + escáner heurístico. Cada vulnerabilidad exige `testable_prediction`, `decisive_test` y `cheapest_probe` → **accionable, no contrarianismo**. Prioridad = severidad × testabilidad. |
| `questions/question_engine.py` | `ScientificQuestion` **vinculada a una vulnerabilidad**; 9 familias; `ScientificQuestionCard` de 15 dimensiones con **fórmula de prioridad transparente** (muestra componentes); `quality_gate` bloquea no-falsables/triviales/ya-respondidas/reformulaciones. |
| `science/discrimination.py` | `RivalSet` (principal + nula + ≥2 rivales), predicciones diferenciales, `DiscriminatingTest`, **ganancia de información esperada** (bits). Una prueba es *decisiva* solo si separa ≥2 hipótesis. |
| `science/pre_research_states.py` | Escalera TOPIC_RECEIVED → … → READY_FOR_EXPLORATORY_RESEARCH. **No se puede saltar de un tema a un experimento confirmatorio.** |
| `epistemic/vulnerability_benchmark.py` | Mide **recall** (halla el fallo conocido) y **especificidad** (no inventa fallos en una afirmación sólida). Preliminar. |

## Caso en vivo (conectado con lo que veníamos haciendo: Caco-2 + Zenodo)

Sobre el hallazgo real "polaridad → menor permeabilidad Caco-2" (confirmado en holdout,
NO replicado):

1. **EVA** halló las mismas debilidades que el panel de 8 voces: `dependencia_fuente`,
   `resultado_no_replicado`, `confusion`, `mecanismo_ambiguo`, `extrapolacion`.
2. **Preguntas** (top, tras el gate): **transportabilidad** ("¿se reproduce en una fuente
   de raíz independiente?") y **dependencia metodológica** ("¿sobrevive al ajustar por
   confusores?").
3. **Rivales + prueba discriminante**: polaridad vs peso molecular vs lipofilia →
   prueba decisiva con **2.00 bits** de información esperada.
4. **Enlace**: la pregunta de transportabilidad activa `replication_finder` → fuente de
   raíz independiente (Zenodo/ChEMBL) para cerrar el hecho #4.

`acero science eva | ask`.

## Correcciones que pidió el revisor (aplicadas)

- La ablación de integridad (100%→0%) queda **reetiquetada como "ablación interna
  preliminar"** (9 casos conocidos), no validación definitiva; falta benchmark ciego con
  splits development/calibration/evaluation y evaluadores externos.

## Honestidad / pendiente

Esto es **maquinaria implementada y probada internamente**, no validada externamente.
Falta (fases del prompt maestro que requieren datos/humanos/tiempo): lineaje de evidencia
completo, EVA con LLM en dos modos sobre literatura real, benchmark ciego de preguntas con
evaluación por expertos, y el caso científico de frontera end-to-end. El andamiaje
computable ya existe.
