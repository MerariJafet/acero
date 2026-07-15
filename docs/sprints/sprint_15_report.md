# Sprint 15 — Unified Research Portal · Report

**Estado:** ✅ Terminado (con decisión de alcance documentada) · **Rama:** `integration/acero-v2-program`

Portal local funcional en `/portal`, servido por FastAPI. **Decisión de alcance:** SPA
vanilla-JS sin build (cero dependencias npm, offline, dentro de `make verify` con pytest) en
lugar de React/Vitest/Playwright — es el fallback documentado de la misión, totalmente
probado. Detalle: `docs/architecture/unified_research_portal.md`.

## Entregado
- Backend `portal/app.py`: agregadores de solo-lectura + acciones seguras bajo `/portal/api/*`,
  montado en la API. Las acciones pasan por los MISMOS servicios protegidos que la CLI — la UI
  **no puede saltarse el gate**. Ningún endpoint expone secretos, tokens crudos ni shell.
- SPA (`static/index.html` + `app.js` + `style.css`): secciones Overview, Research Programs,
  Projects, World Model, Reliability, Red Team, Runtime, Review, Publication Candidates,
  Decision Center, Settings — con **datos reales** del backend (81 reglas de gate, red team
  22/22, review gauntlet, cola de runtime).
- Decision Center: pregunta, contexto, evidencia, contraevidencia, incertidumbre, costo,
  riesgo, aprendizaje requerido, recomendación y **razón para no ejecutar**; APPROVE exige
  razón (espejo de la regla anti-sello del backend).
- Seguridad: CSP estricta, X-Frame-Options DENY, nosniff, static seguro, sin secretos.
- CLI `acero portal`. Tests `tests/integration/test_portal.py` (11).

## Criterios de aceptación
Portal construye/inicia ✓ · API integrada ✓ · sin mocks centrales (datos reales) ✓ · gate
bloquea en UI y backend ✓ · decisiones funcionan ✓ · World Model se visualiza ✓ · reliability
se visualiza ✓ · tests (pytest, no E2E) ✓ · `make verify` los incluye ✓.
Parcial vs. especificación: crear proyecto / ejecutar run desde la UI se hacen vía CLI/API
(la UI muestra estado real y el Decision Center); Vitest/Playwright reemplazados por pytest.

## Calidad
**641 pruebas en verde** (+11), ruff limpio, mypy limpio (268 archivos), `make verify` OK.
