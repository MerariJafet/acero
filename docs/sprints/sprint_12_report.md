# Sprint 12 — Human Scientific Review & Local Publication Preparation · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-sprint-12-scientific-review-publication`

## Qué se construyó
Cierre del roadmap: `src/acero/publication/` ensambla todo (Sprints 1–11) en un expediente
revisable y un **export LOCAL gated** que nunca publica automáticamente.

- **ReviewDossier**: claim central + nivel de inferencia, evidencia a favor Y en contra
  (con conteo de grupos independientes), reliability card + readiness, estado de
  replicación/comprensión/gate, limitaciones, preguntas abiertas, y disclaimers explícitos
  (NO es descubrimiento, NO es publicación, NO es validación experimental).
- **HumanReviewSession**: el humano debe reconocer claim/evidencia/contraevidencia/
  limitaciones/confiabilidad/qué falta validar externamente, demostrar comprensión y
  **declarar una razón**; decisiones APPROVE_FOR_EXTERNAL_REVIEW/REQUEST_CHANGES/REJECT (no
  existe APPROVE_FOR_PUBLICATION); un revisor IA no puede aprobar; hash de contenido ata la
  aprobación al expediente exacto.
- **Export gated**: exige política de publicación (revisión humana, sin auto-publicación),
  readiness = READY_FOR_HUMAN_SCIENTIFIC_REVIEW, comprensión, gate completo, sin
  contradicciones abiertas y aprobación humana vinculante; escribe JSON+Markdown+manifest+
  checksums **solo local**, jamás envía nada; declaración de uso de IA + autoría humana.

## Benchmark
Human Scientific Review Gauntlet: **6/6** (bloqueado sin revisión / no listo / sin
comprensión / revisor IA / contradicción abierta; y un export local aprobado que nunca
auto-publica).

## Auditoría (Codex real)
14 hallazgos; correcciones verificables con regresión: (A) la aprobación **ata al contenido
exacto** (un expediente modificado tras la revisión bloquea el export); (B) una aprobación
exige **una razón declarada** (anti sello automático). Limitaciones declaradas:
"comprensión suficiente" depende del gate de comprensión (Sprint 9); el export no revierte
efectos externos (por eso nunca es automático).

## Calidad
**586 pruebas en verde** (+23), ruff limpio, mypy limpio (253 archivos), `make verify` OK.

## Honestidad científica
`READY_FOR_HUMAN_SCIENTIFIC_REVIEW` es el techo y NO significa publicación ni descubrimiento;
`DISCOVERY_CONFIRMED` no existe; los resultados computacionales no son validación
experimental; nada sale de la máquina automáticamente; el investigador humano es el autor y
la autoridad final.
