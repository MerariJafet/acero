# Sprint 20 — ACERO v2 Release Candidate · Report

**Estado:** ✅ Terminado · **Rama:** `integration/acero-v2-program` · **Versión:** 2.0.0-rc1

## Entregado
- **Versionado:** `2.0.0-rc1` (en `__init__.py` + `pyproject.toml`).
- **Manifiesto de release** (`release/manifest.py`, `docs/releases/release_manifest.json`):
  commit, rama, versión, 31 paquetes, 81 reglas de gate, 8 benchmarks, datasets/licencias,
  seguridad (auto_publication=False), known issues honestos.
- **Instalación:** `make setup` / `make verify` / **`make run`** (portal). Probado limpio.
- **Backup/restore** (`release/backup.py`): `acero backup create|verify|restore` — backup local
  con manifiesto SHA-256; restore **rehúsa** un backup corrupto; **recuperación ante desastre
  probada** (DB corrupta → restore → datos intactos).
- **Aceptación final** (`acero release accept`): corre TODAS las gauntlets — reliability 10/10,
  chaos 12/12, red_team 22/22, mutation 8/8, review 6/6 →
  **RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW**. **Reporta, no aprueba**: un humano decide. Sin
  auto-publicación; sin descubrimiento.
- **Docs de release:** REPORT / LIMITATIONS / SECURITY / REPRODUCIBILITY.

## Criterios de aceptación
Versión ✓ · manifiesto ✓ · install (setup/verify/run) ✓ · backup ✓ · restore probado ✓ ·
disaster recovery ✓ · security review (doc) ✓ · docs ✓ · aceptación final (todas las gauntlets)
✓ · no auto-publicación ✓ · no escritura desprotegida (gate universal + test de arquitectura) ✓.

## Calidad
**656 pruebas en verde** (+8), ruff limpio, mypy limpio (273 archivos), `make verify` OK.

## Limitaciones (ver ACERO_V2_RC1_LIMITATIONS.md)
Sprints 18 (autoevaluación) y 19 (colaboración) NO implementados en este RC. Portal sin
Vitest/Playwright; worker sincrónico; un solo dataset astronómico. Performance baseline:
`make verify` ~60–67 s (656 tests); startup CLI < 1 s; gate/token latencia sub-ms.
