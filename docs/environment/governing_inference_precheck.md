# Pre-chequeo Sprints 8.8–8.9 (Governing Structure Inference Engine)

**Fecha:** 2026-07-13
**Rama de partida:** `feature/acero-cognitive-discovery-engine` (commit `d5b634d`).
**Rama de trabajo:** `feature/acero-governing-structure-inference`.

## Estado verificado
- `git status`: árbol limpio.
- `make verify`: **282 tests verdes**, ruff + mypy limpios.
- Docker (`acero-sandbox:py312`) y Codex CLI `0.144.3` operativos.

## Revisión de lo existente (a reutilizar, no reconstruir)
- **Discovery Engine** (`discovery/`): tournament, EIG, research utility, scheduler,
  next_experiment — se reutilizan para el active loop y priorización.
- **World Model** (`world_model/`): beliefs versionados, contradicciones, anomalías,
  queries — los candidatos inferidos se integran aquí.
- **Cognitive** (`cognitive/`): `dimensions.py` (Buckingham-Pi), `first_principles`
  (model_search, derivations SymPy), `analogies` — se reutilizan para el filtrado
  dimensional de términos y para alimentar analogías desde estructuras inferidas.
- Benchmarks: Hidden Dynamics (Discovery) y Cross-Domain (Cognitive).

## Duplicación / deuda identificada
- `model_search` (cognitive) hace fit de familias fijas; el nuevo motor hará
  **identificación de estructura** (SINDy) — complementario, no duplicado.
- Falta calibración empírica (la señaló la auditoría del Sprint 8) → se construye aquí.
- El "gate epistémico" formaliza la auditoría existente como bloqueo obligatorio.

## Dataset real autorizado
- **SILSO — Número mensual total de manchas solares** (SIDC, Real Observatorio de
  Bélgica), desde 1749. URL: `https://www.sidc.be/SILSO/INFO/snmtotcsv.php`
  (formato `;`, faltantes = -1). **Dominio público**, verificable, referencia
  (Clette & Lefèvre, SILSO). Tamaño < 1 MB. Serie astronómica real con
  **cuasi-periodicidad de ~11 años** y regímenes (mínimos tipo Maunder/Dalton) —
  ideal para: periodicidad, cuasiperiódico vs ruido, huecos, cambio de régimen,
  incertidumbre, y demostrar que NO se infiere el mecanismo físico completo.
  Descarga *gated* (`authorized=True`), hash SHA-256, CSV gitignored.
  NO se declara ningún descubrimiento.

## Arquitectura elegida
`src/acero/inference/` (data/derivatives/noise, variables/relevance, libraries/terms
con filtrado dimensional, discovery/{sparse_identification[SINDy-STLSQ], symbolic_search,
invariants, change_points, conservation}, model_selection/{complexity, stability,
extrapolation, equivalence, identifiability, ranking}, active_experiments/{discriminating,
next_measurement}, calibration, integration, audit + **epistemic gate**). Benchmark
`benchmarks/governing_dynamics.py`. Todo el código de simulación corre en el sandbox.
