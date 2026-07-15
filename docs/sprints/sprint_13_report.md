# Sprint 13 — Consolidation of the 12-sprint roadmap · Report

**Estado:** ✅ Terminado · **Rama:** `integration/acero-v2-program` (desde `c416daf`)

## Consolidación
El historial de los 12 sprints es **perfectamente lineal**: cada rama de sprint es ancestro
directo de la punta de Sprint 12. Verificado: `git log --all --not HEAD` vacío; toda rama es
ancestro de HEAD; árbol limpio. Por tanto **no hubo merges, cherry-picks ni conflictos** —
la rama de integración `integration/acero-v2-program` contiene los Sprints 1–12 con
trazabilidad por commit intacta (sin squash). `master` sin tocar; nada pusheado.

Auditorías Fase 0: `docs/environment/post_v1_git_audit.md`,
`post_v1_architecture_audit.md`, `post_v1_operation_audit.md`, `docs/history/sprint_lineage.md`.

## Schema versioning
- `SchemaVersionRow` (tabla `schema_version`) + `core/schema_version.py`
  (`CURRENT_SCHEMA_VERSION=2`, `ensure_stamped`, `check`). ACERO sigue usando `create_all`
  idempotente; el versionado **detecta** una DB más nueva/vieja y `doctor --deep` lo reporta,
  en vez de correr en silencio contra un esquema incompatible.

## `acero doctor --deep`
Nuevo diagnóstico v2: versión de esquema, políticas + sin servicios de pago, reglas del gate
(81), tokens de mutación (issue/validate/replay-block), schemas exportados al día, disco,
paquetes vestigiales, rama git. Runtime/secrets aparecen como informativos hasta el Sprint 14.

## Depuración
Sin duplicaciones dañinas. Paquetes vestigiales (`hypothesis/contracts.py` sin uso,
`integrations/` y `knowledge/` vacíos) **retenidos** (no borrar procedencia) y documentados;
`doctor --deep` los reporta. MockProvider es el proveedor LLM determinista por defecto (no un
mock de producción que oculte lógica).

## Calidad
**591 pruebas en verde** (+5), ruff limpio, mypy limpio (254 archivos), `make verify` OK.

## Criterios de aceptación
Sprints 1–12 integrados ✓ · ninguna rama con funcionalidad ausente ✓ · make verify pasa ✓ ·
migraciones/bootstrap desde base vacía ✓ (create_all + stamp) · historial por sprint ✓ · sin
conflictos ✓ · gates no debilitados ✓ · comandos principales funcionan ✓ · suite no perdió
pruebas ✓ · commit de integración ✓.

## Limitaciones
Sin Alembic (por diseño; `create_all` + versionado ligero); downgrades no automáticos.
Runtime persistente y secret management llegan en Sprint 14.
