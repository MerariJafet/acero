# ACERO — Dossier de Consolidación (Fase 1 del prompt maestro)
### Auditoría forense del FLUJO REAL con evidencia de código · 2026-08-10

> Generado por un auditor autónomo en modo SOLO-LECTURA sobre el repositorio.
> Regla aplicada: cada afirmación con `path:línea`; lo no verificado se marca UNKNOWN.
> Este documento describe la arquitectura **que existe**, no la deseada. Los
> hallazgos críticos están consolidados en §11 (añadido en la síntesis).

---

## 1. FLUJO REAL de una investigación (modo Bohr v2)

### 1.1 Cadena de llamadas verificada

| Paso | Símbolo | Evidencia |
|---|---|---|
| 1 | `POST /api/projects/{id}/investigate` → `project_investigate()` | `portal/app.py:347-391` |
| 2 | Guard CSRF + anti-duplicado `cycle_running()` (latido `cstat_*`, umbral 6h) | `portal/app.py:353,356-359`; `investigator_bridge.py:87-109` |
| 3 | Claim del body o del `brief`; 422 si no hay | `portal/app.py:360-370` |
| 4 | `record_hypothesis(...)` → kind=`candidate` PROPOSED con DEDUP por claim normalizado | `investigator_bridge.py:39-67` |
| 5 | `mode = body.mode or "bohr"` — **Bohr v2 es el DEFAULT**; `"clasico"` → `run_council` | `portal/app.py:373-383` |
| 6 | BackgroundTask `_attack()` → `run_bohr_cycle()` (excepciones tragadas con `except: pass`) | `portal/app.py:375-386` |
| 7 | provider default `CodexCliProvider` | `investigator_bridge.py:794-812` |
| 8 | Guardián de premisa: `get_premise` + `check_drift`/`drift_warning` como `on_restart` | `investigator_bridge.py:817-825, 1127` |
| 9 | 11 ejecutores reales `executors_raw` envueltos en `_with_log` | `investigator_bridge.py:1080-1097` |
| 10 | `build_knowledge()` (PERSONAS + `toolbox.catalog_text()`), premisa antepuesta | `science/bohr.py:332-338`; `investigator_bridge.py:1120-1123` |
| 11 | `BohrOrchestrator(..., policy="default").run(claim)` | `science/bohr.py:147-178, 269-329` |
| 12 | Por jugada: `_decide()` híbrido → ejecutor → `history.append` → `_on_step` → kind=`decision` con desglose de policy | `science/bohr.py:275-325`; `investigator_bridge.py:1099-1110` |
| 13 | Cierre: `_suggest_next_round()` (kind=`suggestion`), `credence_for(...)`, kind=`report` FOR_STUDY, `_live(done=True)` | `investigator_bridge.py:1135-1180` |

Presupuestos: `max_actions=200`, `wall_budget_s=7 días`, `turing_cap_s=24h`. Guard
anti-bucle: 3 repeticiones idénticas bloquean la jugada. `reiniciar` dispara la
deriva de premisa. `cerrar` solo acepta `HONEST_DISPOSITIONS` — no existen
`solved`/`proved` para un abierto (`science/bohr.py:26-27`).

Herramientas reales por ejecutor: hipatia→`novelty_check` (OpenAlex/arXiv/Crossref
reales), popper→`MathProbe.probe(max_tries=3)`, feynman→`HumanAttitude.observe`,
godel→`MathProbe(formal_first=True)` (sympy+Z3), ramanujan→`SparkEngine.ignite`,
turing→`TuringBuilder.build_and_run`, aristoteles→`CriticAgent`, kepler→`AnomalyEngine`,
noether→`NoetherReviewer.referee`, mendeleev→`patterns.discover_all`, gauss→escribe
`dossier` DRAFT a mano (**NO** llama a `publication/dossier.py`).

### 1.2 Flujos legados coexistentes
- **Clásico**: `run_council()` guion fijo, solo si `mode=="clasico"` (`investigator_bridge.py:369-619`).
- **Spark**: `POST /spark` → `run_spark_flow` (`investigator_bridge.py:700-790`).
- **Misiones/PI loop**: `HypothesisFlow` + `portal/research_loop.py` (un SEGUNDO director autónomo).

→ **Hay 3 orquestadores de decisión coexistiendo** (Bohr v2, ResearchLoop, PI loop). Deuda §10.3.

---

## 2. OBJETOS CIENTÍFICOS (kinds del ledger `discovery`)

Modelo: tabla genérica `DiscoveryRow(id, project_id, kind, status, parent_id, payload JSON)`
(`ledger/models.py:140-155`). **NO es append-only**: `put` sobreescribe, hay
`set_status`, `update_payload` (sin historial) y `delete` (`discovery/store.py:34-134`).

| kind | Creador | Actor | Estados | Evidencia |
|---|---|---|---|---|
| candidate | record_hypothesis | Hilbert/Kepler/Bohr | PROPOSED | `investigator_bridge.py:60-67` |
| experiment | record_result | Popper/Da Vinci | RUN | `investigator_bridge.py:141-152` |
| negative | record_result (refuted) | Popper | CONFIRMED (imborrable) | `store.py:120-132` |
| lemma | record_lemma (+`check_put` degrada proved sin backend mecánico) | Gödel/Euclides | PROVED/FLAGGED/PROPOSED | `permissions.py:44-45` |
| literature | _ex_hipatia | Hipatia | FOUND | `investigator_bridge.py:857-866` |
| critique | CriticAgent | Aristóteles | ISSUED | `portal/critic.py:117` |
| reformulation | record_reformulation | Feynman | PROPOSED | `investigator_bridge.py:162-171` |
| decision | record_decision (+desglose policy) | Bohr | TAKEN | `investigator_bridge.py:196-207` |
| spark/build/review/pattern | ejecutores respectivos | Ramanujan/Turing/Noether/Mendeleev | varios | §1.1 |
| premise | seal_premise (inmutable) | Hilbert | SEALED | `portal/premise.py:91-96` |
| drift | check_drift | Hilbert | FLAGGED | `portal/premise.py:148-152` |
| suggestion/report/council_status | cierre del ciclo | Bohr | — | `investigator_bridge.py:1166-1180` |

`update_payload` (mutación SIN provenance) se usa en ~20 sitios — la mutabilidad
es rutinaria. Ver hallazgo crítico §11.4.

---

## 3. BOHR HÍBRIDO Y SCORES (crítico)

- **Quién genera candidatas:** el LLM. `PolicyEngine.choose` solo elige entre lo
  que el LLM propuso — **el LLM controla el conjunto de opciones**
  (`science/bohr.py:216-223`; `policy.py:103-118`).
- **Scores del LLM** (peso positivo total = 4.0): info, falsabilidad, novedad,
  reducción de incertidumbre, y parte del riesgo. **Todos autodeclarados.**
- **Scores mecánicos:** `ACTION_COST` (0-0.45), `ACTION_RISK` (0.02-0.45, es PISO
  del riesgo), `_repetition_penalty` (medida en las últimas 6 jugadas — no
  manipulable).
- **Candidatas inválidas:** filtradas por `ACTION_MENU`; si ninguna válida →
  camino clásico; si el provider lanza → `cerrar/needs_human_review`. **Nunca se
  queda sin jugada.**
- **¿Puede el LLM inflar para manipular el ranking? SÍ** (hallazgo §11.2): 4.0 de
  utilidad positiva es autodeclarada por el mismo LLM que además elige qué
  candidatas existen; el único piso es el riesgo (≤0.54 de efecto). El docstring
  de policy.py reconoce "señales que el LLM no controla" — cierto solo para
  costo/repetición/piso-de-riesgo.
- **¿El PolicyEngine aprende del historial? NO** — `history` se usa únicamente en
  `_repetition_penalty`. Los costos son tabla estática; el aprendizaje es diseño
  deseado (Research Genome), no arquitectura existente. **Confirma la sospecha del
  revisor.**

---

## 4. CAPABILITY MAP + ALCANZABILIDAD

| Persona | Capability | ¿Ejecutor? | ¿Jugada Bohr? | Alcanzable |
|---|---|---|---|---|
| hipatia/popper/feynman/godel/ramanujan/turing/aristoteles/kepler/noether/mendeleev | (las suyas) | SÍ | SÍ | **SÍ** |
| euclides | symbolic_proof | NO propio | NO | INDIRECTO (dentro de godel/popper) |
| gauss | dossier_packaging | SÍ | SÍ | **PARCIAL**: el ejecutor NO usa el tool declarado |
| **hilbert** | hypothesis_formulation | NO | NO | **inalcanzable como jugada** |
| **euler** | method_selection | NO | NO | **NO** |
| **arquimedes** | data_resolution | NO | NO | **NO** desde Bohr |
| **davinci** | experiment_design | NO | NO | **NO** desde Bohr (solo misiones) |
| tycho | script_memory | NO | NO | INDIRECTO |

**Herramientas potentes SIN jugada de Bohr** (existen pero el director no puede invocarlas):
- `discovery/information_gain.py` → solo un benchmark.
- `inference/active_experiments/discriminating.py` (experimentos discriminantes) → solo un benchmark.
- `inference/discovery/invariants.py` → `inference/engine.py` (fuera del ciclo).
- `inference/discovery/symbolic_search.py` → **CERO importadores (código muerto)**.
- `epistemic/rival_theory_generator.py` → endpoint aparte, no el ciclo.
- `science/sat_escalation.py` → solo como texto en el catálogo TOOLBOX.

→ **Hallazgo §11.6**: el PolicyEngine puntúa "info esperada" y "falsabilidad"
declaradas por el LLM mientras el cálculo REAL de information gain y el diseño de
experimentos discriminantes están desconectados del director. `validate_registry()`
detecta huérfanas pero NO alcanzabilidad — la brecha no se ve en CI.

---

## 5. EXPERIMENTOS: ¿contrato canónico? NO

Hay ≥6 abstracciones paralelas de "experimento". Solo la kind=`experiment` +
`MathProbe` + `TuringBuilder` participan del flujo Bohr. El contrato rico
(`experiment_factory.run_generated` con sha256/artifacts/reproduce-check) **solo lo
usan las misiones**, no Bohr. **Pre-registro, holdout y nulos NO se llaman desde
`run_bohr_cycle`** (grep confirmado): `science/holdout.py` y `science/nulls.py`
tienen CERO importadores. El rigor confirmatorio es de vitrina para el flujo que
más corre (hallazgo §11.5).

---

## 6. LEDGER

- **Dos capas**: ledger tipado (`ledger/service.py`, con invariantes de integridad
  científica y versionado) y store genérico `discovery` (el que usa TODO el flujo vivo).
- **NO append-only**: `update_payload` muta SIN escribir provenance (a diferencia
  de `put`/`set_status`) y se usa en ~20 sitios — **agujero de auditabilidad**.
- **Tamaño real (2026-08-10)**: 67 proyectos, **discovery 4447 filas**, provenance
  6888. Por kind: literature 1142, critique 795, decision 637, watch_scan 632,
  candidate 343, experiment 302, lemma 54, build 49, pattern 18, negative 13,
  drift 2, premise 1…
- **Hallazgo grave §11.3**: el ledger tipado con sus invariantes (question→
  hypothesis→prediction→experiment→run) tiene **0 filas en producción**. Toda la
  ciencia viva está en la tabla genérica con payloads JSON sin schema y mutación
  sin historial. Las garantías del docstring protegen tablas vacías.

---

## 7. ARTEFACTOS Y REPRODUCIBILIDAD

- **MathProbe** (Popper/Gödel): el workspace tempdir se BORRA al terminar; persiste
  solo el veredicto en el payload y el script en una caché global mutable por hash.
  NO persiste: stdout completo, versiones de paquetes, prompt del codegen, semilla
  por corrida.
- **Turing** (`_default_run`): corre el código LLM con `subprocess.run` en un
  tempdir **SIN sandbox, SIN bloqueo de red, con el entorno completo** — hallazgo
  §11.1. Persiste `code[:4000]` (¡truncado!).
- **Contraste**: `experiment_factory` (misiones) SÍ persiste script/stdout/
  provenance.json con sha256/run.sh — dos estándares distintos.
- **¿Reproducible EXACTAMENTE un resultado de la Ronda 5? NO.** Lo único
  exactamente reproducible es re-probar un `lemma` formal (el `z3_claim`/
  `formal_claim` bastan). Todo lo demás depende del LLM no determinista.

---

## 8. FRONTERA DE AUTONOMÍA

- **AUTONOMOUS**: ciclo Bohr completo (200 jugadas/7 días) por un click; codegen +
  ejecución; `pip install` de piezas; búsquedas HTTP reales; escritura de todos los kinds.
- **POLICY-APPROVED**: trabajos GPU (`GPU_POLICY`, hoy `approved_by_human=False` →
  rebotan a humano); sandbox bajo política.
- **HUMAN-REQUIRED**: validación final de disposiciones; publicación (reviewer DEBE
  ser humano); sellado de premisa; borrado; activar driver GPU; commits git.
- **FORBIDDEN**: declarar resuelto un abierto; texto LLM como evidencia (se
  degrada); borrar negativos; red/código peligroso dentro del sandbox.
- **Grieta §11.1**: el FORBIDDEN de red aplica al sandbox de MathProbe/factory pero
  NO al `_default_run` de Turing — inconsistente entre ejecutores.

---

## 9. TESTS (176 archivos, 143 en unit)

Unit (con providers fake) 143, integración 8, e2e 1 (Playwright), gauntlets
científicos 11, seguridad/caos 5-6, property-based 8. **Test de camino completo
mission→bohr→policy→tool REAL→evidence→ledger: PARCIAL** — existen tres tests que
encadenan `run_bohr_cycle` con `BohrOrchestrator` monkeypatcheado o provider fake
(`test_patterns.py:97`, `test_premise.py:101`, `test_upgrade.py:52`), pero ninguno
con herramienta real (MathProbe/sandbox de verdad) en una sola corrida.

---

## 10. CÓDIGO DESCONECTADO Y DEUDA

**Muertos** (cero importadores desde el flujo vivo): `evaluation/`,
`inference/discovery/symbolic_search.py`, `science/holdout.py`, `science/nulls.py`,
`experiment/workflow.py`. **Solo-catálogo/benchmark**: `sat_escalation.py`,
`information_gain.py`, `discriminating.py`, `invariants.py`. **Zombi**: ledger
tipado (entities/runs/decisions con 0 filas).

**Duplicaciones**: 5 críticos (critic/experiment_critic/skeptic/llm_skeptic/noether),
3+ de novedad, ≥6 de "experimento", 2 de pre-registro, 2 de research_loop, 3 orquestadores.

### Top 10 de deuda (del auditor, por riesgo)
1. Turing ejecuta código LLM sin sandbox ni bloqueo de red.
2. Manipulabilidad del PolicyEngine (4.0 autodeclarado).
3. Ledger tipado vacío; ciencia en JSON libre mutable.
4. `update_payload` muta sin provenance (~20 sitios).
5. Irreproducibilidad de los experimentos del Consejo.
6. Prereg/holdout/nulos/discriminating desconectados del ciclo autónomo.
7. Capacidades registradas inalcanzables + `_ex_gauss` que no usa su tool.
8. Módulos muertos (incluido `sat_escalation`, la técnica estrella documentada).
9. Duplicación de críticos/novelty/experimento/directores.
10. `record_hypothesis` O(n) por dedup; errores de background tragados con `except: pass`.

---

## 11. HALLAZGOS CRÍTICOS (síntesis — requieren decisión)

Estos son los que cambian la calificación y piden tu criterio antes de la siguiente cirugía:

1. **[SEGURIDAD] Turing sin sandbox** (`turing.py:61-70`): Bohr puede, de forma
   autónoma, hacer que Turing ejecute código generado por LLM con red abierta y
   entorno completo. Contradice la promesa constitucional. *Prioridad 1.*
2. **[EPISTÉMICO] PolicyEngine manipulable**: mi Bohr híbrido mejora la forma pero
   el fondo del score sigue siendo autoevaluación del LLM. La solución del revisor
   (proposer vs mechanical vs historical estimate) es correcta y hoy solo tengo la
   interfaz, no el estimador mecánico real de info/novedad. *Prioridad 1.*
3. **[ARQUITECTÓNICO] Ledger tipado vacío**: la ciencia vive en la tabla genérica.
   Las invariantes de integridad no protegen nada. *Prioridad 2.*
4. **[AUDITABILIDAD] `update_payload` sin provenance**: agujero en el argumento
   central "todo queda en el ledger". *Prioridad 2.*
5. **[RIGOR] Prereg/holdout/nulos/discriminating desconectados**: existen y no se
   usan en el ciclo que más corre. Conectar > construir. *Prioridad 2.*
6. **[DESCUBRIMIENTO] Information gain real desconectado**: Bohr puntúa "info
   esperada" declarada mientras el cálculo real está en un benchmark. *Prioridad 2.*
7. **[REPRODUCIBILIDAD] Experimentos del Consejo no reproducibles exactamente**.
   *Prioridad 3.*
