# ADR-0009: Domain Labs, gate in-line y grader híbrido

- **Estado:** Aceptado
- **Fecha:** 2026-07-14

## Contexto
Sprint 10 exige (1) que ninguna mutación científica relevante se salte el gate, (2)
laboratorios que razonen dentro de cada ciencia y declaren sus límites, y (3) un grader que
reconozca paráfrasis válidas sin dar autoridad a Codex.

## Decisión
- **Gate in-line** (`epistemic_gate/enforcement.py`): `enforce()` gate-then-mutate;
  bloqueo = sin mutación + registro de rechazo; contexto thread-local + `BypassDetected`;
  overrides restringidos con reglas no overridables.
- **Domain Labs** (`domains/core` + 4 labs): contrato `ScientificDomain` + `DomainResultClass`
  que impide inflar una simulación a validación; reglas de dominio; benchmarks 8/8 con el
  caso que el gate bloquea.
- **Grader híbrido** (`understanding/grading/`): determinista autoridad; Codex advisory que
  solo eleva a PASS_WITH_REVIEW con fragmento citado; jamás MASTERED.
- Los 4 plugins antiguos se movieron a `<domain>/plugin.py` bajo los nuevos paquetes.

## Alternativas descartadas
- Ejecutar el gate DESPUÉS de mutar (rechazado: dejaría estado defectuoso).
- Dar a Codex autoridad para calificar dominio (rechazado por la constitución).
- Presentar simulaciones como validación (rechazado: clasificación estructural).

## Consecuencias
- (+) 7/7 bypasses bloqueados; 4 labs 8/8; grader sin falsos positivos ni engañado por
  ataques.
- (−) Superficie protegida acotada al World Model; contexto thread-local no cruza
  async/subproceso; clases de dominio y checkers son un subconjunto — todo declarado.
