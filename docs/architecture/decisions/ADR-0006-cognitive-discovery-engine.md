# ADR-0006: Cognitive Discovery Engine sobre análisis dimensional verificable

- **Estado:** Aceptado
- **Fecha:** 2026-07-13

## Contexto
Los Sprints 8.5–8.7 exigen representar significado, descubrir estructura compartida y
razonar desde primeros principios — sin confundir lenguaje profundo con comprensión, y
sin que la salida de Codex sea evidencia.

## Decisión
Paquete `src/acero/cognitive/` con tres motores y una base compartida de **análisis
dimensional verificable** (`dimensions.py`, Buckingham-Pi por null space racional). Las
analogías se deciden por pruebas estructurales/dimensionales/predictivas (transferencia
verificada en el sandbox), no por embeddings ni por similitud verbal (peso 0.05). Las
derivaciones se verifican con SymPy. Los conceptos y analogías se persisten como nodos/
aristas del World Model (extensión, no duplicación). Codex propone; ACERO valida.

## Alternativas descartadas
- Embeddings como criterio de analogía (rechazado: mide similitud verbal, no estructura).
- Aceptar derivaciones de LLM sin verificación (rechazado por la constitución).

## Consecuencias
- (+) Resultados verificables: oscilador↔RLC soportado con transferencia de resonancia
  simulada; átomo↔sistema solar marcado engañoso; péndulo/energía por dimensiones.
- (+) Corre offline (mock) para tests; ejecución real con Codex demostrada (mapeo
  completo + auditoría de 10 hallazgos, correcciones con pruebas de regresión).
- (−) Formas estructurales y grupos adimensionales son de un catálogo (no inferencia
  arbitraria todavía).
- (−) Buckingham-Pi no fija constantes numéricas (declarado explícitamente).

## Nota Codex
`--output-schema` (OpenAI structured outputs) exige todas las propiedades en `required`
y NO admite mapas abiertos: los mapeos se codifican como arrays de pares {from,to}.
