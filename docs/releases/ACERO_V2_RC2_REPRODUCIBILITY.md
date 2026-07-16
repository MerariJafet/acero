# ACERO 2.0.0-rc2 — Reproducibility

- `make verify` (ruff + mypy + policy + schemas + 698 tests) determinista.
- **Baseline RC1 firmado** en `evaluation/baselines/v2.0.0-rc1/` (resultados + hash + firma);
  la detección de regresiones compara contra él con tolerancias prerregistradas.
- **Benchmark runner** registra commit, versión, ambiente y duración por corrida.
- **External review bundles** llevan `version_binding.json` (commit + hashes de artefactos) y
  `checksums.txt`; un review solo aplica a la versión/hash que declara.
- Datos reales (SILSO, exoplanets) con URL/licencia/hash; caché gitignored.
- Backup/restore con manifiesto hasheado; recuperación ante desastre probada.

## Límites
Diferencias BLAS/numpy entre máquinas pueden alterar dígitos finales; comparaciones dentro del
mismo entorno. Codex advisory no es bit-reproducible; MockProvider determinista por defecto.
