# Sprint 11 — Scientific Reliability & Adversarial Assurance · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-sprint-11-scientific-reliability`

## Universal Inline Gate
- **Write surface inventory** (`docs/security/write_surface_inventory.md`): ninguna ruta
  científica central queda `LEGACY_UNPROTECTED`. Test de arquitectura que falla si un módulo
  no-boundary importa persistencia directamente.
- **Contexto async-safe** (`contextvars`): `GateExecutionContext` propaga a asyncio/tasks;
  NO se hereda en hilos/subprocesos; `require_context(action=...)` bloquea fuera de contexto
  o para otra acción.
- **Tokens de mutación**: HMAC firmados, single-use, con TTL, ligados a acción+proyecto+
  artefactos; rechazan tamper/expiración/replay/proyecto/acción/artefacto equivocados.
- **Unit of Work** multi-store con rollback (PREPARED→…→COMMITTED/ROLLED_BACK/FAILED); un
  fallo no deja confianza parcial ni pierde el intento.

## Evidencia, independencia y replicación
- Grafo de dependencia (dataset/muestra/pipeline/simulador/derivado/sistemático/analista/
  método) + clusters; `dependency_aware_support` evita inflar soporte por duplicados.
- Niveles de replicación: reejecución (misma semilla) NO es replicación independiente.
- `EvidenceQuality` multidimensional (nunca colapsa en un solo número en silencio).

## Calibración formal
- `CalibrationRegistry`: Brier/log-loss/ECE/MCE/reliability/sharpness/coverage/risk-coverage/
  abstención; separada por dominio/tarea/dificultad/versión; declara `INSUFFICIENT`.
- Recalibración (binning/temperature/interval inflation) en split de calibración; rechaza
  solape calibración/test (leakage).

## Scientific Red Team
- Biblioteca versionada de 22 ataques (datos/estadística/modelos/literatura/humano/dominio)
  cableados al detector REAL → **22/22 detectados**.
- Mutation testing científico (unidades/baseline/control/prereg/dataset/negativos) →
  **8/8 atrapados**.
- Codex advisory: propone ataques, nunca declara el sistema seguro.

## Robustez por dominio
Física (convergencia por refinamiento + estabilidad), astronomía (red-noise vs señal),
genética (multiple testing + estructura), química (masa + rigidez + no identificabilidad).

## Reliability Scorecard
- `ScientificReliabilityCard` (sin trust score mágico), niveles de readiness con techo
  `READY_FOR_HUMAN_SCIENTIFIC_REVIEW` (`DISCOVERY_CONFIRMED` no existe), y
  `PublicationCandidate` que **nunca publica automáticamente**.

## Benchmark integral
Scientific Reliability Gauntlet: **10/10 tracks** (incl. bypass concurrente 8/8 bloqueado y
abstención correcta por datos insuficientes).

## Auditoría (Codex real)
10 hallazgos; correcciones verificables con regresión: (A) id huérfano `harking` →
`metrics_prespecified` (regla real); (B) dependencia por analista/método humano añadida;
tests de regresión para ambos + "mutation testing corre n>0". Limitaciones declaradas: UoW
no revierte efectos externos irreversibles; secreto de token por-proceso.

## Calidad
**562 pruebas en verde** (+68), ruff limpio, mypy limpio (247 archivos), `make verify` OK.

## Honestidad científica
Reproducible ≠ correcto; independiente ≠ verdadero; calibrado ≠ validado. Lo validado solo
en simulación NO está validado experimentalmente. `READY_FOR_HUMAN_SCIENTIFIC_REVIEW` no
significa publicación ni descubrimiento.
