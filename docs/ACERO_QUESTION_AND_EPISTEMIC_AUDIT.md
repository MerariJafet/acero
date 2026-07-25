# F0 — Auditoría del flujo actual (tema → pregunta → hipótesis)

Entregable de la Fase 0. Verificado contra el repositorio, no solo la documentación.

## Dónde nace hoy una pregunta/hipótesis

| Punto | Módulo | Cómo |
|---|---|---|
| Generación de hipótesis | `portal/hypotheses.py` | Codex (`complete_json`) o fallback determinista; el humano da el tema/proyecto |
| Orientación a descubrimiento | `portal/novelty.py` + `hypotheses.py` | filtro de novedad (asentada/en_debate/abierta/inexplorada) + ángulos (cross_data/anomaly/…) |
| Anomalías → hipótesis | `portal/anomalies.py` | residuos/discrepancias medidas → hipótesis origin=anomaly |
| Crítica | `portal/critic.py` (Aristóteles) + `portal/panel_review.py` (8 voces) | tras cada tarea |

**Hueco identificado (raíz del 3er dictamen):** hoy ACERO **parte de una hipótesis** (dada
o generada) y la ejecuta con rigor. NO parte de un **tema general**, reconstruye el
conocimiento, halla dónde podría fallar, y *deriva* preguntas fértiles de esas
vulnerabilidades. Falta la cadena: comprender→reconstruir→vulnerabilidad→pregunta→rivales→
prueba discriminante.

## Matriz de capacidades (estado real tras las últimas iteraciones)

| Capacidad | Implem. | Integr. | Test unit | E2E/vivo | Valid. externa |
|---|---|---|---|---|---|
| Constitución científica (19 módulos) | ✅ | ✅ dossier | ✅ 110+ | ✅ Caco-2 | ❌ |
| IndependenceGraph | ✅ | parcial | ✅ | ✅ PAMPA | ❌ |
| Ablación de integridad | ✅ | n/a | ✅ | ✅ | ❌ (interna preliminar) |
| ClaimReconstructor (F1) | ✅ | — | ✅ | ✅ | ❌ |
| EVA vulnerabilidades (F3) | ✅ núcleo | — | ✅ | ✅ | ❌ |
| Motor de preguntas (F4) | ✅ núcleo | — | ✅ | ✅ | ❌ |
| Rivales + prueba discriminante (F6/F7) | ✅ núcleo | — | ✅ | ✅ | ❌ |
| Evidence lineage (F2) | ❌ | — | — | — | ❌ |
| Orquestador constitucional (F8) | ❌ | — | — | — | ❌ |
| Modelo del Mundo epistémico (F9) | ❌ | — | — | — | ❌ |
| Benchmark con splits + métricas (F10/F11) | parcial | — | ✅ vuln | — | ❌ |

## Riesgos de regresión
- Los paquetes nuevos (`epistemic/`, `questions/`) son **aditivos**; no tocan el flujo del
  portal ni la fábrica. Riesgo bajo.
- El Modelo del Mundo epistémico (F9) se implementa como grafo NUEVO y autocontenido
  (`epistemic/knowledge_graph.py`), no modifica `world_model/` existente → riesgo mínimo.

## Plan (F1–F12)
F1 reconstrucción ✅ · F2 lineaje de evidencia · F3 EVA completa · F4 máquina de preguntas
completa · F5 control de calidad ✅ · F6 rivales · F7 pruebas discriminantes ✅ · F8
orquestador constitucional · F9 grafo de conocimiento · F10/F11 benchmark con splits +
métricas · F12 caso en vivo + entregables.

**Estado de calidad de arranque:** 856 tests verdes, ruff y mypy limpios, master intacto.
