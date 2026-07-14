# ADR-0005: World Model como grafo de creencias versionado

- **Estado:** Aceptado
- **Fecha:** 2026-07-13

## Contexto
El Sprint 8 exige un "modelo vivo del conocimiento", no un grafo de documentos.
Cada investigación debe cambiar lo que ACERO cree; nada debe existir fuera del
World Model; no debe haber verdades absolutas.

## Decisión
Grafo epistémico persistente en `src/acero/world_model/` con tablas nuevas
(`world_nodes`, `world_edges`, `world_node_history`). Nodos = creencias con
`BeliefState`; aristas tipadas con peso/confianza. Reglas duras: beliefs se
actualizan/versionan (nunca se sobrescriben), relaciones se debilitan/inactivan
(nunca se borran), `link` idempotente, `max_confidence < 1`. Contradicciones y
anomalías son motores que **crean nodos y abren preguntas**, no marcadores inertes.
El Discovery Engine alimenta el World Model vía `update.integrate_hidden_dynamics`.

## Alternativas descartadas
- Un grafo de papers/citas (rechazado por la misión: sería una base de datos).
- Neo4j (dependencia pesada innecesaria; NetworkX es suficiente como adaptador de
  lectura, la verdad vive en SQL versionado).

## Consecuencias
- (+) El grafo aprende y es auditable: historial por creencia, procedencia por
  cambio, memoria científica consultable.
- (+) Corre offline; el dato real (exoplanetas) confirma que cambia correctamente.
- (−) Detección de contradicciones por *stance* estructural, no semántica libre.
- (−) Falta un estado posterior competitivo normalizado entre modelos y una
  ontología temporal más rica (backlog, señalado por la auditoría Codex).

## Auditoría
`world_model/audit.py` (reglas + Codex). La auditoría real produjo 15 hallazgos;
los verificables se corrigieron con pruebas de regresión (redundancia de aristas,
aprendizaje disperso, relaciones que no se debilitaban).
