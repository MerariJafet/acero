# Sprint 9 — Human Understanding Engine + Global Epistemic Gate · Reporte

**Estado:** ✅ Terminado · **Rama:** `feature/acero-human-understanding-engine`

## Parte A — Human Understanding Engine (`src/acero/understanding/`)
- **Modelo del investigador**: máquina de estados de conocimiento (UNKNOWN…MASTERED +
  MISCONCEIVED/DECAYED); cada transición exige evidencia de desempeño; MASTERED requiere ≥4
  tipos de evidencia distintos (una sola respuesta nunca da dominio).
- **Evidencia de comprensión**: 12 tipos de tareas (explicar, predecir, detectar error,
  transferir, proponer falsación, decir qué no se puede concluir, …).
- **Misconceptions**: catálogo de 13 confusiones clásicas, detección con conciencia de
  negación; se resuelven solo con NUEVA evidencia, no con una explicación leída.
- **Currículum por investigación**: requisitos derivados de SINDy, analogía y manchas
  solares, anclados a ecuaciones/código/supuestos reales; grafo de prerrequisitos (ciclos,
  ruta mínima, conceptos fundacionales, dependencias redundantes).
- **Explicaciones por niveles** (intuición → frontera), cada nivel con limitaciones;
  modos EXPLAIN_* (la abstención debe dar causa concreta, no "confianza baja").
- **Predicción previa** bloqueada tras revelar el resultado (anti-HARKing humano);
  detección de sobreconfianza; incertidumbre honesta no penalizada.
- **Assessments** (rúbrica, crédito parcial, guarda anti-keyword-echo), transferencia
  cross-domain, ejercicios (solución oculta hasta el intento), preguntas por nivel de Bloom.
- **Gate de comprensión**: bloquea decisiones críticas por debajo del nivel requerido; no
  bloquea tareas de bajo riesgo; override humano trazable con razón obligatoria.
- **Historial** append-only + revisión espaciada; **dashboard HTML** funcional;
  **auditoría pedagógica** (reglas + Codex real).

## Parte B — Global Epistemic Gate (`src/acero/epistemic_gate/`)
- Capa transversal obligatoria con **81 reglas deterministas** en 11 etapas
  (Literature → Publication).
- Generaliza las 14 reglas del gate de inferencia (Sprint 8.9) sin duplicarlas.
- Estados PASS / PASS_WITH_WARNINGS / BLOCKED / ESCALATE_TO_HUMAN / BLOCKED_FOR_LEARNING.
- **Input ausente → advertencia "no evaluable"**, nunca un pase silencioso.
- **Codex advisory**: solo advertencia salvo que nombre una regla; promover un hallazgo a
  regla exige checker + prueba.
- **Policy bridge**: costos/publicación/seguridad/autonomía aparecen como gate results
  (sin reglas contradictorias duplicadas).

## Benchmark
Human-in-the-Loop Scientific Understanding Benchmark (4 casos + transferencia + predicción):
SINDy (bloquea novedad), analogía (rechaza equivalencia sin falso positivo), manchas
solares (periodicidad≠mecanismo), gate adversarial BLOCKED (5 bloqueadores, humano detecta
1.0), transferencia aprobada, predicción bloqueada con sobreconfianza detectada.

## Auditoría (Codex real)
Deterministas: 0 hallazgos estructurales. **Codex pedagógico real: 11 hallazgos.**
Correcciones verificables aplicadas con regresión: (1) guarda de **keyword-echo** en el
grader; (2) chequeo de **estado incoherente con la habilidad demostrada** en la auditoría.

## Calidad
**428 pruebas en verde** (+93), ruff limpio, mypy limpio (201 archivos), `make verify` OK.
5 schemas nuevos exportados.

## Limitaciones / honestidad
"Dominio" = desempeño demostrado en varios tipos de tarea sobre los conceptos de una
decisión, NO comprensión perfecta. El grader es determinista (cobertura de elementos):
puede perder matices y depende de rúbricas; por eso se exigen varios tipos de evidencia, se
penalizan afirmaciones prohibidas y el eco de palabras clave, y Codex nunca certifica
comprensión. Aprobar una evaluación es evidencia, no prueba, de comprensión.
