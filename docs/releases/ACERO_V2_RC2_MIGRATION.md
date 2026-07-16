# ACERO 2.0.0-rc2 — Migration Notes

## Desde RC1 (o una DB v1/v2)
- **Esquema:** `CURRENT_SCHEMA_VERSION = 3`. `create_all` es idempotente: al iniciar, ACERO crea
  las tablas nuevas (`schema_version`, `runtime_tasks/tokens/events`) automáticamente. No se
  requiere migración manual. `acero doctor --deep` reporta la versión de esquema y avisa si la DB
  es más nueva que el código.
- **Sin Alembic:** downgrades no automáticos. Para revertir a RC1, usa el tag `v2.0.0-rc1` y una
  DB compatible (v≤3); `doctor --deep` detecta incompatibilidad y rehúsa escribir.

## Secretos (Sprint 14, sin cambios en RC2)
- Producción exige `ACERO_HMAC_SECRET` (`acero secrets init`). Development usa un secreto
  efímero etiquetado. Los tokens no sobreviven un reinicio salvo con secreto de entorno
  compartido.

## Baselines de evaluación
- El baseline RC1 (`evaluation/baselines/v2.0.0-rc1/`) queda como referencia. Para fijar un
  baseline RC2: `acero evaluation lock-baseline v2.0.0-rc2`.

## Compatibilidad
- Python 3.12; SQLite por defecto (PostgreSQL opcional vía los mismos modelos). Sin cambios de
  API que rompan RC1 (solo endpoints/CLI nuevos).
