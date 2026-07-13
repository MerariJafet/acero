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

## Riesgos abiertos (documentados, no resueltos)
1. El sandbox de subproceso es más débil que un contenedor/nsjail. Para código
   **no confiable** de terceros, migrar a Docker `--network=none --read-only` o
   nsjail (Sprint 7+). El piloto ejecuta código propio y determinista.
2. El screening estático es por patrones; es defensa en profundidad, no una
   garantía. El aislamiento de runtime es la barrera principal.
3. No hay control de acceso multiusuario (fuera de alcance v1).
