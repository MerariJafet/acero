# ADR-0004: Discovery Engine como paquete único con LLM advisory

- **Estado:** Aceptado
- **Fecha:** 2026-07-13

## Contexto
Los Sprints 5–7 requieren un motor que convierta preguntas en experimentos que
reduzcan incertidumbre: generación de hipótesis, torneo, diseño experimental,
ganancia de información, ejecución, actualización de confianza, creación de
herramientas. Riesgo central: que la "inteligencia" resida en prompts y que la
salida del LLM se trate como evidencia.

## Decisión
Un paquete `src/acero/discovery/` (monolito modular, no microservicios). La lógica
científica vive en clases/funciones **deterministas y verificables**; Codex es
**advisory** en generación, crítica y auditoría, siempre detrás de `complete_json`
con un contraparte mock. Persistencia en una tabla genérica `discovery` con
procedencia por evento. Ejecución siempre en el sandbox existente.

## Consecuencias
- (+) Todo el motor corre offline (mock) para tests; ≥1 ejecución real con Codex
  demostrada (generación diversa + auditoría de 18 hallazgos).
- (+) Las decisiones (generar/rankear/podar/actualizar/aprobar) quedan en
  procedencia; reproducibles.
- (+) Nada se borra: rechazadas y negativos preservados por diseño.
- (−) La diversidad es léxica+estructural (sin embeddings); documentado.
- (−) Codex estructurado es lento (modelo de razonamiento); el default es mock.

## Nota sobre schema de Codex
`--output-schema` (structured outputs de OpenAI) exige que **todas** las
propiedades estén en `required`; el schema de generación se ajustó en consecuencia.
