# Sprint 18 — Continuous Scientific Self-Evaluation · Report

**Estado:** ✅ Terminado · **Rama:** `feature/acero-v2-rc2-sprints-18-19`

## Scientific Capability Evaluation Engine (`src/acero/selfeval/`)
Mide continuamente si ACERO mejora, empeora o solo añade complejidad. **Nunca se autoaprueba,
nunca autoedita producción, y NO trata más tests/código como mejora científica.**

- **Capability Registry** (`capabilities.py`): 14 capacidades con estado dirigido por
  EVIDENCIA (EXPERIMENTAL/SUPPORTED/DEGRADED/UNRELIABLE/BLOCKED/DEPRECATED). Astronomía queda
  **EXPERIMENTAL** (un solo dataset) — el motor **nunca auto-promueve** un EXPERIMENTAL a
  SUPPORTED aunque su benchmark pase; promover es decisión humana.
- **Benchmark Registry + Runner** (`benchmarks.py`): 7 benchmarks reales centralizados con
  thresholds **prerregistrados** (no se editan tras ver resultados); cada corrida registra
  commit, versión, ambiente, duración.
- **Baseline Locking** (`baseline.py`): baseline **firmado** de RC1 en
  `evaluation/baselines/v2.0.0-rc1/`; `load` detecta modificación silenciosa (firma + hash);
  rehúsa sobrescribir sin `--force`.
- **Regression Detection** (`regression.py`): IMPROVED/UNCHANGED/REGRESSED/INCONCLUSIVE/
  INSUFFICIENT_DATA con **tolerancias prerregistradas** por métrica (una variación pequeña no
  es regresión); latencia incluida (menor-es-mejor).
- **Failure Memory** (`failures.py`): sembrada con los **fallos reales corregidos** en v2
  (surrogate de fase, sobre-conteo de ciclos, keyword-echo, id huérfano, dependencia por
  analista, aprobación sin binding) — cada uno con su test de regresión.
- **Improvement Proposals** (`proposals.py`): exigen evidencia + rollback; **nunca se aplican
  automáticamente**; solo un humano las mueve más allá de PROPOSED.
- **Prompt Evaluation** (`prompts.py`): evalúa prompts de 8 agentes contra fixtures
  controlados (offline); respuestas **inseguras o sobreafirmantes FALLAN**.
- **Codex Drift** (`codex_drift.py`): fingerprint del proveedor;
  `CODEX_PROVIDER_REVALIDATION_REQUIRED` si cambia. Funciona offline; Codex advisory.
- **Tool Evaluation** (`tools.py`): marca herramientas degradadas (bloquear/reemplazar/
  deprecar; nunca usar en silencio).
- **Portal:** sección **Self-Evaluation** (benchmarks, capacidades, regresión, prompts).
- **CLI:** `acero evaluation run/status/history/lock-baseline/failures`.

## Resultado de la corrida
7/7 benchmarks pasan; **NO_REGRESSION** vs baseline RC1; 14 capacidades (astronomía
EXPERIMENTAL); 2/4 fixtures de prompt pasan (los adversariales fallan como deben).

## Calidad
**676 pruebas en verde** (+20), ruff limpio, mypy limpio (285 archivos), `make verify` OK.

## Honestidad
Autoevaluación **no** significa que ACERO comprenda sus límites como un humano. El Benchmark
Registry **no** es evaluación independiente (son benchmarks propios, con sesgos declarados).
Reporta evidencia; un humano decide.
