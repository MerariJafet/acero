# ACERO 2.0.0-rc2 — Release Candidate Report

**Rama:** `feature/acero-v2-rc2-sprints-18-19` (desde `887fc45`, con tag `v2.0.0-rc1`
congelado) · **Estado:** Release Candidate (revisión humana pendiente). RC1 permanece
reproducible e intacto.

## Novedades vs RC1
- **Sprint 18 — Scientific Capability Evaluation Engine** (`src/acero/selfeval/`): capability
  registry (14 capacidades, sin auto-promoción), benchmark registry + runner con thresholds
  prerregistrados, **baseline RC1 firmado** (`evaluation/baselines/v2.0.0-rc1/`), detección de
  regresiones, failure memory (fallos reales de v2 con test), improvement proposals
  (evidencia+rollback, nunca auto-aplicadas), evaluación de prompts (fixtures offline), codex
  drift, tool evaluation. CLI `acero evaluation`.
- **Sprint 19 — Collaboration & External Review Preparation** (`src/acero/collaboration/`):
  workspaces, external review bundle con version binding, import estructurado (nunca
  auto-confiado, version-bound), issue tracker, response drafts (aprobación humana), planes de
  validación externa, autoría CRediT (IA nunca autora), licensing (bloquea desconocido/
  incompatible). CLI `acero collab`.

## Aceptación final (`acero release accept`)
reliability 10/10 · chaos 12/12 · red_team 22/22 · mutation 8/8 · review 6/6 ·
**self_evaluation NO_REGRESSION** · **external_review 11/11** →
**RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW**. Reporta, no aprueba.

## Calidad
**698 pruebas en verde**, ruff limpio, mypy limpio, `make verify` OK, 33 paquetes, 81 reglas de
gate. Backup/restore probado; recuperación ante desastre probada.

## Instalación
`make setup` · `make verify` · `make run` (portal). Ver `ACERO_V2_RC2_MIGRATION.md`.

Ver también RC2_{LIMITATIONS,SECURITY,REPRODUCIBILITY,MIGRATION}.md y `release_manifest.json`.
