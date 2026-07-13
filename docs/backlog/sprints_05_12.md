# Backlog — Sprints 5 a 12

Cada sprint hereda las reglas de la Constitución y la definición de "terminado"
(código que ejecuta + pruebas + criterios demostrados + limitaciones registradas).

## Sprint 5 — Motor de hipótesis y torneo de ideas
- Generación de hipótesis diversas (varios ángulos), con supuestos explícitos.
- Clustering de ideas y detección de duplicados semánticos.
- Comparaciones emparejadas + ranking multiobjetivo (falsabilidad, utilidad,
  novedad preliminar).
- Escéptico reforzado; registro de hipótesis descartadas (con motivo).
- **Depende de:** ledger (2), `hypothesis/` (contratos ya esbozados).
- **Riesgo:** falsa "creatividad"; mitigar con estructura y evaluación, no prompts.

## Sprint 6 — Diseño experimental avanzado
- Controles, ablation studies, análisis de sensibilidad e incertidumbre.
- Diseños factoriales, comparación con baselines, validación cruzada.
- Criterios de detención y presupuesto computacional; priorización por ganancia
  de información (`ResearchUtility`).
- **Depende de:** ciclo (4).

## Sprint 7 — Motor de experimentos y búsqueda
- Ejecución paralela controlada, colas, checkpoints, reanudación segura.
- Búsqueda de hiperparámetros: bayesiana y evolutiva; árbol de experimentos.
- Cancelación por bajo valor esperado.
- **Endurecer sandbox** a Docker `--network=none --read-only` o nsjail.
- **Depende de:** 6 y sandbox (4).

## Sprint 8 — Modelo del mundo y grafo científico
- Grafo de afirmaciones (NetworkX inicialmente): evidencia, contraevidencia,
  relaciones causales, contradicciones.
- Actualización bayesiana **configurable** e historial de creencias.
- Visualización del grafo.
- **Depende de:** ledger (2), resultados (4/7).

## Sprint 9 — Tutor científico y aprendizaje humano
- Perfil de conocimientos + evaluación inicial.
- Explicaciones por niveles, preguntas socráticas, ejercicios, derivaciones.
- Predicción humana previa vs modelo; ruta de aprendizaje.
- **Extiende:** `pedagogy/` (semilla del Sprint 4).

## Sprint 10 — Especialización científica (plugins)
- Física, astronomía, genética computacional, química computacional.
- Cada plugin: tipos de datos, herramientas permitidas, validaciones, unidades,
  simuladores, riesgos, plantillas, benchmarks. **Sin wet-lab autónomo.**
- **Depende de:** 6/7.

## Sprint 11 — Evaluación, auditoría y ciencia adversarial
- Benchmarks internos, calidad de citas, calibración, tasa de errores,
  reproducibilidad, robustez, evaluación de novedad.
- Red-teaming científico: sesgo de confirmación, p-hacking agéntico, HARKing,
  data leakage; auditoría independiente.
- **Transversal:** corre desde el Sprint 5.

## Sprint 12 — Publicación, colaboración y portal
- Dashboard maduro (React/TS/Vite/Tailwind).
- Export a Markdown/PDF/LaTeX; notebooks reproducibles; paquetes de replicación.
- Metadatos DOI-ready y ORCID-ready; checklist de publicación.
- **Verificación humana obligatoria; nunca publicar automáticamente.**
- **Depende de:** export (2) + revisión humana.
