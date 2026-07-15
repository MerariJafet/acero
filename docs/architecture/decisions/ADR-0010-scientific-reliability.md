# ADR-0010: Scientific Reliability & Adversarial Assurance

- **Estado:** Aceptado
- **Fecha:** 2026-07-14

## Contexto
Sprint 11 exige demostrar cuáles capacidades merecen confianza: gate universal, contexto
async, tokens, rollback multi-store, dependencia de evidencia, calibración, red team, y
readiness sin sobreafirmar.

## Decisión
- Gate universal (`epistemic_gate/{transaction[contextvars],tokens,unit_of_work}`) +
  guardas en todas las mutaciones centrales + test de arquitectura de import.
- `reliability/` (evidence, calibration, recalibration, red_team, mutation,
  domain_reliability, scorecard, engine) + `benchmarks/reliability_gauntlet.py`.
- Readiness con techo `READY_FOR_HUMAN_SCIENTIFIC_REVIEW`; `DISCOVERY_CONFIRMED` NO se
  implementa; `PublicationCandidate` sin publicación automática.

## Alternativas descartadas
- Un único "trust score" mágico (rechazado: tarjeta multidimensional).
- Contexto thread-local (insuficiente para async → contextvars).
- Contar reejecución como replicación (rechazado explícitamente).
- Tokens reutilizables/persistidos (rechazado: single-use, por-proceso).

## Consecuencias
- (+) 22/22 ataques detectados, 8/8 mutaciones atrapadas, gauntlet 10/10, bypass
  concurrente bloqueado.
- (−) UoW no revierte efectos externos; secreto de token por-proceso; calibración requiere
  n≥8 — declarado.
