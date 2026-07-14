# Backlog actualizado — Sprints 8 a 12

Tras completar el Discovery Engine (Sprints 5–7), el backlog se refina así.

## Sprint 8 — Modelo del mundo y grafo científico
- Grafo de afirmaciones (NetworkX) sobre las entidades del ledger + candidatos.
- Relaciones causales/contradicciones; actualización bayesiana configurable
  reutilizando `discovery/confidence.py`.
- Historial de creencias (ya hay procedencia CONFIDENCE_UPDATE que lo alimenta).
- Visualización del grafo (dashboard, Sprint 12).
- **Depende de:** ledger (2), confidence (7).

## Sprint 9 — Tutor científico y aprendizaje humano
- Perfil de conocimientos + evaluación inicial; extiende `pedagogy/` y los
  `learning/*.md` que ya genera el benchmark.
- Explicaciones por niveles, preguntas socráticas, predicción humana previa vs
  modelo, ruta de aprendizaje.

## Sprint 10 — Especialización científica (ampliar)
- Ya existen plugins iniciales (física, astronomía, genética, química).
- Integrar los simuladores de dominio como *herramientas permitidas* dentro del
  Discovery Engine (generación/experimentos por dominio) vía el `ToolRegistry`.
- Benchmarks y validación dimensional por dominio.

## Sprint 11 — Evaluación, auditoría y ciencia adversarial (prioritario)
- Ya existe `benchmarks/audit.py` (rules + Codex) y correcciones aplicadas.
- Formalizar: **calibración** (curvas de fiabilidad, cobertura), p-hacking/HARKing
  agéntico, data leakage sistemático, red-teaming continuo desde Sprint 5.
- Convertir el auditor en un gate opcional del pipeline.

## Sprint 12 — Publicación, colaboración y portal
- Dashboard (React/TS/Vite/Tailwind) sobre la API existente (incl. endpoints de
  descubrimiento).
- Export Markdown/PDF/LaTeX; notebooks reproducibles; DOI/ORCID-ready.
- **Verificación humana obligatoria; nunca publicar automáticamente.**

## Deuda técnica transversal a atender
- Migraciones Alembic reales para las tablas nuevas (`discovery`).
- Recuperación semántica local (embeddings) para diversidad e ingestión.
- Backends de sandbox más fuertes (nsjail/gVisor) para código no confiable.
- Optimización bayesiana/evolutiva/active learning (interfaces ya declaradas).
