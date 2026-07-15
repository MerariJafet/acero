# ACERO 2.0.0-rc1 — Release Candidate Report

**Rama:** `integration/acero-v2-program` · **Estado:** Release Candidate (revisión humana pendiente)

## Qué es
ACERO v2 RC1: un **instituto de investigación computacional personal** local-first. Integra los
12 sprints de v1 más el trabajo v2 (consolidación, runtime persistente, portal, Program OS,
programa astronómico real). NO finge universidad, laboratorios físicos ni revisión por pares.

## Instalación (limpia)
```bash
make setup     # venv --system-site-packages + install -e .[dev]
make verify    # ruff + mypy + policy + schemas + 656 tests
make run       # portal local en http://127.0.0.1:8000/portal/
```

## Aceptación final (todas las gauntlets)
`acero release accept` → reliability 10/10 · chaos 12/12 · red_team 22/22 · mutation 8/8 ·
review 6/6 → **RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW**. La aceptación **reporta**, no aprueba: un
humano decide. Sin publicación automática; sin afirmación de descubrimiento.

## Backup / recuperación
`acero backup create|verify|restore` — backup local con hashes SHA-256; restore rehúsa un
backup corrupto; recuperación ante desastre probada (DB corrupta → restore → datos intactos).

## Alcance v2 entregado
- Sprint 13 consolidación + schema versioning + `doctor --deep`.
- Sprint 14 runtime persistente (workers, leases, heartbeats, tokens cross-process, chaos 12/12).
- Sprint 15 portal unificado (SPA vanilla-JS servida por FastAPI, datos reales, gates en UI).
- Sprint 16 Research Program OS (portfolio multidimensional, budget duro, retrospectivas).
- Sprint 17 programa astronómico real (SILSO; 11.2yr, significativo vs ruido rojo AR(1); sin
  descubrimiento).
- Sprint 20 release candidate (versión, manifiesto, backup/restore, aceptación).

## Métricas de calidad
656 pruebas en verde, ruff limpio, mypy limpio, `make verify` OK, 31 paquetes, 81 reglas de gate.

Ver también: `ACERO_V2_RC1_LIMITATIONS.md`, `ACERO_V2_RC1_SECURITY.md`,
`ACERO_V2_RC1_REPRODUCIBILITY.md`, `release_manifest.json`.
