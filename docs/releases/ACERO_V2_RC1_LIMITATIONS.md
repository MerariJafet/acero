# ACERO 2.0.0-rc1 — Known Limitations (honest)

## Sprints v2 NO ejecutados en este RC
- **Sprint 18** (Autoevaluación continua) y **Sprint 19** (Colaboración / revisión externa):
  no implementados. El RC prioriza P0/P1 (integridad, runtime, portal, programa real, release).

## Limitaciones por componente
- **Portal (15):** SPA vanilla-JS sin build (sin Vitest/Playwright); probado con pytest
  (rutas/DOM/seguridad). Crear proyecto / ejecutar run desde la UI aún van por CLI/API.
- **Runtime (14):** el worker drena sincrónicamente (sin daemon de larga vida; requiere gestor
  de procesos externo). Concurrencia entre procesos OS separados no ejercida en tests unitarios.
- **Program OS (16):** vínculo program↔subproyectos↔World-Model por id (no auto-sincronizado).
- **Astronomía (17):** un solo dataset (SILSO); descomposición multi-componente no exhaustiva;
  dependencia de instrumento/pipeline no evaluada. **No es validación experimental.**
- **Persistencia:** sin Alembic (create_all idempotente + versionado ligero); downgrades no
  automáticos. Secreto HMAC por defecto efímero en development.

## Honestidad científica
Nada se publica automáticamente. `DISCOVERY_CONFIRMED` no existe. El techo es
`READY_FOR_HUMAN_SCIENTIFIC_REVIEW`. Los resultados computacionales NO son validación
experimental. El análisis astronómico NO afirma mecanismo, causalidad ni descubrimiento.
