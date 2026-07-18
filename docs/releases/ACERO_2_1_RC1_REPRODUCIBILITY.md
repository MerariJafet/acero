# ACERO 2.1.0-rc1 — Reproducibility

## Standalone package
`reproduction/transit_kepler8b/` depends only on numpy/scipy/astropy and imports
**no** ACERO. A static check fails if any file imports `acero`.

## Independent-process reproduction (evidence)
Isolated Docker container (fresh OS/Python/cache, no ACERO state) downloaded its own
public Kepler data (**hashes match the manifest, no drift**) and recovered the
known period with three independent methods:

```
state: INDEPENDENT_PROCESS_REPRODUCTION   (NOT external replication)
BLS 3.52326 d | PDM 3.52326 d | matched-box 3.52221 d | is_discovery: false
```

See `docs/benchmarks/independent_process_reproduction_output.txt` and
`docs/benchmarks/transit_cleanroom_docker_output.txt`.

## Determinism
Preregistration is SHA-256 hashed before analysis; synthetic experiments are
seeded; every download records URL/provider/date/license/size/SHA-256/schema.

## Backup / restore
`acero backup create|verify|restore` — SHA-256 manifest; restore refuses on a
failed verification; round-trip proven (`verify_backup_roundtrip`).
