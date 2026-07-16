# Full v2 Diff Review (Sprint 21)

Diff `master..feature/acero-v2-rc2-sprints-18-19` (RC2):  587 files changed, 44671 insertions(+), 3 deletions(-)

## By area (20 commits, Sprints 1–20 + 18/19)
- **Módulos:** 33 paquetes en `src/acero/` (core→release). 294 módulos importan sin error.
- **Seguridad:** gate in-line universal (contextvars, tokens de mutación single-use), sandbox,
  secretos HMAC de entorno, publicación automática prohibida, test de arquitectura de write
  surface.
- **Persistencia:** SQLite + `create_all` idempotente + schema_version v3 (runtime/schema
  tables). Alembic pendiente (Sprint 22).
- **Portal:** SPA vanilla-JS servida por FastAPI, secciones con datos reales, CSP.
- **Ciencia:** discovery, world model, cognitive, governing inference, domain labs,
  reliability, un programa astronómico real (SILSO).
- **Docs:** reportes por sprint (1–20 + 18/19), ADRs 0007–0011, releases RC1/RC2, constitución
  14b–14m.
- **Tests:** 701 en verde (unit/property/science/integration/security).

## Estrategia de merge
La historia de RC2 es **lineal** y `master` es su ancestro directo ⇒ el merge a master es un
**fast-forward** (sin merge commit, sin squash, tags preservados). Verificado en el ensayo.
