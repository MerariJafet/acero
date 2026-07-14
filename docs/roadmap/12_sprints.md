# ACERO — Roadmap de 12 Sprints

Los Sprints 1–4 están **implementados y verificados** en esta entrega. Los
Sprints 5–12 están **planificados** (ver `docs/backlog/sprints_05_12.md`).

| # | Nombre | Estado | Entregable central |
|---|---|---|---|
| 1 | Fundación, constitución y control | ✅ Hecho | Config, políticas+guard, logging, CLI, API, sandbox base, `make verify` |
| 2 | Expediente científico y modelo de conocimiento | ✅ Hecho | Entidades epistémicas, ledger con integridad, historial, procedencia, export |
| 3 | Biblioteca científica y procedencia | ✅ Hecho | Ingestión local, chunking, BM25, verificación de citas, métricas de recuperación |
| 4 | Ciclo mínimo de investigación computacional | ✅ Hecho | Workflow, prereg, sandbox run multi-semilla, escéptico, reproducibilidad, piloto |
| 5 | Motor de hipótesis y torneo de ideas | ✅ Hecho | Generación (Codex+mock), diversidad, falsabilidad, torneo multiobjetivo+Elo, descartadas preservadas |
| 6 | Diseño experimental y ganancia de información | ✅ Hecho | Experimentos discriminantes, EIG bayesiano+heurística, utilidad transparente, stopping rules, críticos |
| 7 | Motor de ejecución, búsqueda y aprendizaje | ✅ Hecho | Árbol de investigación, scheduler, búsqueda, confidence update, tool creation, next experiment |
| 8 | Modelo del mundo y grafo científico | ✅ Hecho | Grafo epistémico vivo (creencias), contradicciones, anomalías, programas, evolución, narrador, dato real (Kepler), visualización |
| 8.5–8.7 | Cognitive Discovery Engine | ✅ Hecho | Concept Engine, Analogy Engine (oscilador↔RLC verificado), First Principles Engine (dimensiones/Buckingham-Pi/derivaciones SymPy) |
| 8.8–8.9 | Governing Structure Inference Engine | ✅ Hecho | SINDy/STLSQ, invariantes, regímenes, identificabilidad, experimentos discriminantes, calibración, gate epistémico; dato real (manchas solares) |
| 9 | Human Understanding Engine + Global Epistemic Gate | ✅ Hecho | Modelo del investigador (evidencia de desempeño), misconceptions, currículum por investigación, explicaciones por niveles, predicción previa, gate de comprensión con override, y gate epistémico transversal (81 reglas, 11 etapas) |
| 10 | Scientific Domain Labs + Inline Gate + Hybrid Grader | ✅ Hecho | 4 labs computacionales (física/astronomía/genética/química) con clasificación de resultado y reglas de dominio; gate epistémico in-line obligatorio (bloqueo transaccional, bypass detection); grader híbrido (determinista + Codex advisory) |
| 9 | Tutor científico y aprendizaje humano | ⏳ Backlog | Perfil, evaluación, explicaciones por niveles, ruta de aprendizaje |
| 10 | Especialización científica | 🟡 Parcial | Plugins iniciales física/astronomía/genética/química (sin wet-lab), 14 benchmarks verdes — `docs/domains/plugins.md` |
| 11 | Evaluación, auditoría y ciencia adversarial | ⏳ Backlog | Benchmarks, calibración, red-teaming, p-hacking/HARKing/leakage |
| 12 | Publicación, colaboración y portal | ⏳ Backlog | Dashboard, export Markdown/PDF/LaTeX, DOI/ORCID-ready, revisión humana |

## Extensiones entregadas fuera de la secuencia
- **Sandbox Docker endurecido** (adelanto de endurecimiento del Sprint 7):
  `--network=none --read-only --cap-drop=ALL`, imagen `acero-sandbox:py312`.
- **Proveedor LLM Codex CLI** (`codex exec`) como runtime local seleccionable
  (`ACERO_LLM_PROVIDER=codex`), reemplazando la vía Ollama por decisión del PI.
- **Plugins de los 4 dominios** (avance del Sprint 10).

## Prioridad y dependencias
- 5 y 6 dependen del ledger (2) y del ciclo (4) — ya presentes.
- 7 depende de 6 (diseños a ejecutar) y del sandbox (4) — endurecer a Docker/nsjail.
- 8 depende del ledger (2) y de resultados (4/7).
- 9 extiende `pedagogy` (semilla en 4).
- 10 depende de 6/7 (herramientas por dominio).
- 11 es transversal y debe correr continuamente desde 5 en adelante.
- 12 depende de 2 (export) y de revisión humana obligatoria.

## Alcance de esta entrega
Profundidad real en 1–4 (código que ejecuta, pruebas que pasan, artefactos
documentados) por encima de cobertura superficial de los 12.
