# Backlog Sprints 10–12 (actualizado tras Sprint 9)

Estado: Sprints 1–9 implementados y verificados. Lo que sigue son las líneas estratégicas
pendientes; ver también `docs/backlog/sprints_09_12_updated.md` (deuda transversal).

## Sprint 10 — Integración obligatoria del gate + comprensión en el bucle
- Cablear el **Global Epistemic Gate** in-line como barrera obligatoria en cada commit de
  conocimiento (Discovery, World Model, Cognitive, Inference), no solo disponible.
- Emitir en cada acción de investigación el par `ScientificUpdate` + `HumanUnderstandingUpdate`.
- Visualización del **grafo de conocimiento humano** integrada con el Concept Engine.

## Sprint 11 — Robustez y calibración
- Grader semántico (más allá de cobertura de elementos) para reducir dependencia de rúbricas.
- Intervalos de confianza calibrados para coeficientes de inferencia (bootstrap disponible).
- Robustez numérica entre entornos (tolerancias explícitas; heredado del estándar de repro).

## Sprint 12 — Preparación para publicación (siempre con revisión humana)
- Gate de publicación conectado a un flujo de export local revisado (sin publicación
  automática, por constitución).
- Reportes de comprensión: qué aprendió el investigador por proyecto.

## Deuda transversal
Ver `docs/backlog/sprints_09_12_updated.md`.
