# ADR-0008: Human Understanding Engine y Gate Epistémico Global

- **Estado:** Aceptado
- **Fecha:** 2026-07-14

## Contexto
Sprint 9 exige que ACERO no convierta al investigador en espectador de reportes
sofisticados, y que ningún resultado entre como conocimiento aceptado sin pasar un gate en
su etapa.

## Decisión
- `src/acero/understanding/`: modelo del investigador con transiciones exigidas por
  evidencia de desempeño, misconceptions, currículum derivado de investigaciones reales,
  explicaciones por niveles, predicción previa, assessments, transferencia y un gate de
  comprensión con override humano trazable.
- `src/acero/epistemic_gate/`: 81 reglas deterministas en 11 etapas; generaliza (no
  duplica) el gate de inferencia; input ausente = advertencia no-evaluable; Codex advisory;
  políticas puenteadas.
- Persistencia sobre la tabla genérica `discovery` (sin migración Alembic nueva).

## Alternativas descartadas
- Inferir comprensión del autorreporte o de una explicación de Codex (rechazado: no es
  evidencia de desempeño).
- Reescribir la lógica de las 14 reglas de inferencia en el gate global (rechazado: se
  generaliza con un adaptador para no contradecirse).
- Un sistema educativo/SRS sofisticado (fuera de alcance: revisión espaciada heurística).

## Consecuencias
- (+) El humano debe demostrar comprensión (varios tipos de evidencia) antes de decisiones
  críticas; puede disentir con override registrado.
- (+) Un reporte defectuoso queda BLOCKED por el gate global en su etapa.
- (−) El grader es determinista y puede perder matices; "dominio" es desempeño demostrado,
  no comprensión perfecta — declarado.
