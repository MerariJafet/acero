# ACERO 2.0.0-rc2 — Known Limitations (honest)

## Lo que la autoevaluación NO es (Sprint 18)
- **NO es evaluación independiente:** usa los benchmarks propios de ACERO, con sesgos
  declarados; un pase no valida la ciencia, solo que el detector propio no cambió.
- **NO significa** que ACERO comprenda sus límites como un humano. Reporta evidencia; un humano
  decide. No auto-promueve capacidades (astronomía sigue EXPERIMENTAL).

## Lo que la preparación de revisión NO es (Sprint 19)
- **Un review bundle NO es revisión externa.** Nada se envía ni se contacta.
- **Importar un review NO legitima al revisor** (nunca auto-confiado; version-bound).
- **Un plan de validación externa NO es validación** (nada se ejecuta).
- **La IA nunca es autora.**

## Heredadas de RC1
- Portal sin Vitest/Playwright (pytest route/DOM/security). Worker sincrónico. Un solo dataset
  astronómico. Sin Alembic (create_all idempotente + versionado ligero v3). Secreto HMAC
  efímero en development.

## Antes del merge / publicación
- **Antes del merge a master:** revisión humana del diff completo (commits `human_required`).
- **Antes de cualquier publicación:** revisión científica externa real (aún no ocurrida),
  validación experimental donde aplique. `2.0.0-rc2` NO está listo para producción pública.
