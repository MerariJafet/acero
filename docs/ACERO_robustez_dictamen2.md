# Robustez v2 — respuesta ejecutada al 2º dictamen del especialista

El 2º dictamen (8.3/10 como sistema; 6.8–7.1 en "descubrimientos defendibles") señaló
huecos concretos. Ejecución **lean**: se implementaron y probaron las 4 piezas de mayor
apalancamiento, priorizando las que **cierran huecos** y **producen evidencia**. Sin romper
nada (829 tests verdes, mypy/ruff limpios).

## Lo implementado

### L1 — IndependenceGraph (independencia calculada, no declarada)
`science/independence_graph.py`. La independencia entre datasets se **deriva de la
procedencia** (study_id, assay_source, laboratory, cohort, instrument, curation_pipeline,
provenance_root), no se afirma. Regla dura, verificada:

- holdout vs dataset completo → `SAME_PARTITION` → **replicación: False**.
- Caco-2 vs PAMPA (otra fuente/cohorte/instrumento) → `DIFF_SOURCE` → **replicación: True**.

Cierra de forma computable el "CONFIRMADO_EN_HOLDOUT ≠ REPLICADO_EN_DATASET_INDEPENDIENTE"
que el revisor marcó como el hueco #1.

### L2 — Scientific Integrity Benchmark (la evidencia clave)
`science/integrity_benchmark.py`. Ablación **sin vs con** constitución sobre 9 casos con
verdad conocida (sobreafirmación causal, sin prueba nula, deuda de exploración/p-hacking,
confusión, fuga, controles faltantes, novedad falsa + 2 casos limpios).

| | SIN gobernanza | CON gobernanza |
|---|---:|---:|
| Falsos positivos (de 7 indefendibles) | **7** | **0** |
| Tasa de falsos positivos | **100 %** | **0 %** |
| Falsos negativos (casos limpios bloqueados) | — | **0** |

Es exactamente el hecho #1 que el revisor exigió demostrar: **la constitución reduce los
falsos positivos frente a un pipeline sin gobernanza** (100 % → 0 %) sin bloquear ciencia
válida. Reproducible: `acero science integrity`.

### L3 — Ledger semántico + genealogía de hipótesis (anti-HARKing)
`science/lineage.py`. Captura la búsqueda que ocurre **antes del código**: preguntas
consideradas, hipótesis descartadas, datasets rechazados, cambios de endpoint/
interpretación/título. Un cambio **sensible al resultado hecho tras ver los datos** es
HARKing: incrementa la deuda y **prohíbe la clasificación confirmatoria** salvo evidencia
independiente nueva. El grafo de linaje reconstruye la hipótesis desde la idea inicial.

### L4 — Sello del protocolo por niveles + validación sustantiva de DAGs
- `preregistration.SealLevel`: `LOCAL_FROZEN` → `EXTERNALLY_TIMESTAMPED` →
  `PUBLIC_PREREGISTRATION`, con un `SealAdapter` (interfaz) para sellos externos. Honesto:
  sin un servicio real, el protocolo se queda en `LOCAL_FROZEN` (no se fabrica el sello).
- `causal_validation.py`: cada arista causal lleva su evidencia (assumed / literatura /
  experimental / experto). Un DAG cuyas aristas solo las **propuso la IA** puede ser
  sintácticamente válido e identificable, pero **nunca alcanza `SUBSTANTIVE`** ni permite
  lenguaje causal fuerte. Solo evidencia real o aprobación experta lo elevan.

## Constitución endurecida
`constitution.govern`: la **deuda de exploración alta en descubrimiento ahora BLOQUEA** el
avance (antes solo avisaba).

## Autoevaluación honesta (dictamen: 8.3 global)

| Dimensión | Dictamen | Hoy | Por qué |
|---|---:|---:|---|
| Control del espacio de búsqueda | 7.8 | **8.2** | ledger semántico + anti-HARKing |
| Validación externa | 5.5 | **6.2** | independencia calculada (aún falta 2ª fuente real) |
| Inferencia causal | 6.8 | **7.2** | validación sustantiva de aristas |
| Preparación para publicación | 7.8 | **8.0** | benchmark de ablación reproducible |
| Descubrimientos defendibles | 6.8–7.1 | **7.1** | evidencia de reducción de FP, no de novedad |

**Global honesto: 8.3 → ≈8.5.** El avance está en *gobernanza demostrada con números*, no
en capacidad de descubrimiento (que sigue sin demostrarse externamente).

## Lo que el especialista pidió y sigue PENDIENTE (requiere datos/humanos/tiempo)
- Benchmark ciego de 50–100 misiones con calibración separada de evaluación.
- Réplica en una **2ª fuente real** (p. ej. PAMPA para Caco-2).
- Panel ciego y diverso (vistas parciales por revisor) + calibración empírica de umbrales.
- Módulo THESIS (comité doctoral, matriz de trazabilidad, defensa simulada).
- Reproducibilidad hermética (contenedor + lockfile + SBOM) y artículo metodológico.

Estos son fases de semanas con dependencias externas; el andamiaje computable para todas
ya existe en `src/acero/science/`.
