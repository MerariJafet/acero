# Modelo de amenazas de ACERO

Alcance: sistema local-first, un solo usuario (el investigador), sin exposición a
Internet por defecto. Las principales superficies de riesgo son la **ejecución de
código de experimentos** y la **fuga de secretos/costos**.

| Amenaza | Vector | Mitigación | Prueba |
|---|---|---|---|
| Código de experimento malicioso/erróneo | script en sandbox | screening estático + `python -I` + env sin secretos + límites de recursos + timeout | `tests/security/test_sandbox.py` |
| Exfiltración por red desde el sandbox | sockets/urllib | red deshabilitada (preámbulo runtime) + screening de patrones | `test_network_blocked_at_runtime` |
| Fuga de secretos al código ejecutado | `os.environ` | `env` mínimo; `os.environ` **no** se pasa al hijo | `test_secrets_not_leaked_into_sandbox` |
| Escape del workspace (path traversal) | escrituras fuera de `cwd` | `cwd`=workspace, política `workspace_only` | `test_writes_confined_to_workspace` |
| Fork bomb / agotamiento | procesos/CPU/mem | `RLIMIT_NPROC/CPU/AS`, `setsid`+kill de grupo | `test_timeout_is_enforced` |
| Gasto accidental en servicios de pago | LLM/nube | `costs.yaml` off + circuit breaker + `PolicyGuard` | `test_cost_guard_*` |
| Publicación/envío accidental | export/email | `publication.yaml` + `check_publication` | `test_publication_requires_human_review` |
| Cita fabricada (alucinación) | referencias inventadas | verificación contra documentos ingeridos | `test_citation_verifier_rejects_fabricated` |
| Manipulación de resultados (HARKing) | editar hipótesis tras ver datos | guarda que marca ediciones post-resultado en procedencia | `test_harking_guard_...` |
| Borrado de resultados negativos | delete | bloqueado para `NEGATIVE_RESULT` | `test_negative_result_cannot_be_deleted` |
| Herramienta generada maliciosa/errónea | tool creation | screen → sandbox obligatorio → benchmark → quarantine | `tests/security/test_tool_creation.py` |
| Path traversal en herramienta generada | `../`, `/etc/` | screening dedicado + sandbox | `test_path_traversal_blocked` |
| Borrado de hipótesis rechazadas / negativos de descubrimiento | delete | bloqueado en `DiscoveryStore.delete` | `test_rejected_candidates_cannot_be_deleted`, `test_negative_store_delete_blocked` |
| Sobreconfianza / falsa precisión | confidence update | verosimilitud templada + etiqueta "no calibrada" | `test_confidence_not_overconfident` |
| Fork bomb / agotamiento en scheduler | tareas | timeout + aislamiento de fallos + cancelación | `tests/unit/test_discovery_scheduler.py` |
| Descarga externa no autorizada | dataset real | `download_exoplanets(authorized=True)` obligatorio + cap de 5 MB + host fijo HTTPS | `world_model/ingest.py` |
| Verdades absolutas / sobreconfianza en el World Model | belief update | `max_confidence<1`, suavizado, penalizaciones; auditor de reglas | `tests/unit/test_world_belief.py`, `test_world_audit.py` |
| Pérdida de conocimiento (overwrite/delete) | grafo | beliefs versionados; relaciones se inactivan, no se borran; anomalías/negativos preservados | `tests/unit/test_world_graph.py`, `test_world_contradictions_anomalies.py` |
| Analogía superficial aceptada como profunda | cognitive | similitud verbal peso 0.05; pruebas estructural/dimensional/predictiva; caso engañoso marcado | `tests/unit/test_cognitive_analogies.py` |
| Derivación de Codex sin verificar | cognitive | SymPy verifica cada paso; pasos no resueltos registrados; confianza <1 | `tests/unit/test_cognitive_first_principles.py` |
| Razonamiento conceptual circular | cognitive | dependencias acíclicas rechazan ciclos | `test_cognitive_concepts.py::test_circular_dependency_rejected` |
| Transferencia predictiva ejecuta código | analogía | corre en el sandbox (subprocess/docker), sin red | `cognitive/analogies/validation.py` |
| Fuga en identificación (derivadas del mismo dato) | inference | declarado en cada reporte; caveat SINDy | `tests/unit/test_inference_active_calibration.py` |
| Conclusión más fuerte que la evidencia | inference | gate epistémico bloquea; nivel declarado; abstención | `tests/unit/test_inference_gate.py` |
| Descarga externa no autorizada (manchas solares) | inference | `download_sunspots(authorized=True)` + cap + host fijo | `benchmarks/real_astronomy_inference.py` |
| Código de simulación fuera del sandbox | inference | transferencias/experimentos corren en el sandbox | `cognitive/analogies/validation.py` |
| Comprensión humana simulada (autorreporte/LLM como evidencia) | understanding | dominio exige varios tipos de evidencia de desempeño; Codex nunca certifica | `tests/unit/test_understanding_learner.py`, `test_understanding_gate_engine.py` |
| Grader que siempre aprueba / eco de palabras clave | understanding | rúbrica determinista + penalización de forbidden + guarda anti-keyword-echo | `test_understanding_security.py`, `test_understanding_assessment.py` |
| Alteración de una predicción tras revelar el resultado | understanding | predicción bloqueada al revelar (anti-HARKing humano) | `test_understanding_security.py::test_prediction_cannot_be_altered_after_reveal` |
| Sobrecolección de datos personales | understanding | perfil local mínimo; auditoría marca campos sensibles | `test_understanding_security.py::test_profile_privacy_overcollection_flagged` |
| Gate paternalista / bloqueo excesivo | understanding | tareas de bajo riesgo nunca bloqueadas; override humano con razón | `test_understanding_gate_engine.py::test_low_risk_decision_never_blocked` |
| Conocimiento defectuoso aceptado sin gate | epistemic_gate | 81 reglas por etapa; input ausente = advertencia no-evaluable; pipeline se detiene en BLOCKED | `tests/unit/test_epistemic_gate.py` |
| Codex legislando el gate | epistemic_gate | advisory salvo que nombre una regla; promover exige checker + prueba | `test_epistemic_gate.py::test_promotion_requires_checker_and_test` |
| Mutación científica que salta el gate | epistemic_gate | `enforce()` corre el gate ANTES de mutar; escritura protegida fuera de contexto lanza BypassDetected | `tests/unit/test_inline_gate.py`, `benchmarks/gate_bypass.py` |
| Estado parcial tras un bloqueo | epistemic_gate | gate-then-mutate; rollback; sin mutación si bloquea | `test_inline_gate.py::test_blocked_mutation_leaves_no_state` |
| Override de una regla crítica | epistemic_gate | reglas no-overridables (fabricación/seguridad/procedencia/autoría/publicación) | `test_inline_gate.py::test_override_refused_on_non_overridable` |
| Simulación presentada como validación física | domains | clasificación de resultado + regla de dominio bloquea | `tests/unit/test_domain_labs.py::test_simulation_not_claimed_as_validation` |
| Asociación presentada como causalidad | domains | regla `association_not_causal` bloquea | `test_domain_labs.py::test_association_not_causal_blocked` |
| Petición peligrosa (patógeno/toxina/explosivo) | domains | screening de tokens prohibidos en genética/química | `tests/security/test_sprint10_security.py` |
| Manipulación del grader (inyección/copia de rúbrica) | understanding | autoridad determinista; Codex advisory nunca da dominio; eco/contradicción fallan | `tests/unit/test_hybrid_grader.py`, `test_sprint10_security.py` |

## Riesgos abiertos (documentados, no resueltos)
1. El sandbox de subproceso es más débil que un contenedor/nsjail. Para código
   **no confiable** de terceros, migrar a Docker `--network=none --read-only` o
   nsjail (Sprint 7+). El piloto ejecuta código propio y determinista.
2. El screening estático es por patrones; es defensa en profundidad, no una
   garantía. El aislamiento de runtime es la barrera principal.
3. No hay control de acceso multiusuario (fuera de alcance v1).
