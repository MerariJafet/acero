# ACERO 2.0.0-rc1 — Reproducibility

- **Gate de calidad:** `make verify` (ruff + mypy + policy + schemas + 656 tests) determinista.
- **Datos reales:** SILSO sunspots y NASA exoplanets registran URL, licencia, referencia y
  **hash SHA-256**; caché gitignored; análisis determinista dado el CSV.
- **Programa astronómico:** FFT/bootstrap/AR(1)-surrogates con semillas fijas → resultados
  reproducibles dado el dataset. El período 11.19 yr y el IC [10.27, 11.67] se reproducen.
- **Runtime:** cola/tokens/eventos persistidos; reejecución tras "reinicio" ve el estado
  guardado (checkpoints). Tokens single-use por-proceso (no sobreviven reinicio, por diseño).
- **Backup/restore:** manifiesto con hashes; restore rehúsa un backup corrupto; round-trip y
  recuperación ante desastre probados.
- **Manifiesto de release:** `docs/releases/release_manifest.json` (commit, versión, paquetes,
  reglas de gate, benchmarks, datasets, known issues).

## Límites
Diferencias de BLAS/numpy entre máquinas pueden alterar dígitos finales; comparaciones dentro
del mismo entorno registrado. Codex (opcional) no es bit-reproducible (servicio externo);
MockProvider determinista es el default offline.
