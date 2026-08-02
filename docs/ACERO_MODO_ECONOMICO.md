# ACERO — Modo Económico

Tercer modo (Aprender / Investigar / **Economía**). Diálogos e ideas para **generar
recursos y sostener una economía sana** (crecimiento + estrategia de gasto),
cimentado en las **finanzas reales de NEXUS**. El asesor **cuestiona cada idea
hasta que funcione**. Reglas duras: nunca inventa cifras; no ejecuta transacciones;
no es asesoría de inversión licenciada — **planea, el humano decide**.

## Fuente de datos: NEXUS (read-only)
`src/acero/integrations/nexus.py` resuelve en orden: (1) API NEXUS
(`ACERO_NEXUS_URL`, `ACERO_NEXUS_TOKEN`; FastAPI en :8000/:8003 con /summary,
/balance, /accounts), (2) snapshot local `acero_data/economics/nexus_snapshot.json`
(import manual o push de NEXUS), (3) si no hay nada → `available:false` (sin
inventar). Normaliza a {ingresos, gastos, neto, gastos_por_categoría, cuentas}.

## Dashboard (3 paneles)
- **Izquierda — NEXUS $**: ingresos/gastos/neto, gasto por categoría (barras),
  cuentas, fuente. Si no hay datos, invita a conectar/importar.
- **Centro — asesor**: análisis anclado al snapshot, **ideas de crecimiento**
  (cada una con 🔎 Cuestionar y 🚀 Promover) y caja de diálogo.
- **Derecha — estrategia**: salud financiera (0..1), gráfico SVG del LLM,
  estrategia de gasto, riesgos.

## Loop de crítica ("cuestionar hasta que funcione")
`POST /api/economics/{sid}/critique` evalúa una idea adversarialmente contra el
snapshot → `viable | needs_work | reject` + `fixes` + `viability_score`. Iteras
hasta que sea viable, luego `promote` la guarda como proyecto económico.

## Endpoints / archivos
- `GET /api/economics` (sesiones + snapshot), `POST /start`, `GET /{sid}`,
  `POST /{sid}/ask`, `POST /{sid}/critique`, `POST /{sid}/promote`.
- `src/acero/portal/economics.py` (EconomicEngine/Advisor; sesión en
  `acero_data/economics/<sid>/`), `integrations/nexus.py`,
  `static/js/economics.js` + selector en `app.js`.
- Tests: `tests/unit/test_economics.py`, `tests/unit/test_nexus_connector.py`.
