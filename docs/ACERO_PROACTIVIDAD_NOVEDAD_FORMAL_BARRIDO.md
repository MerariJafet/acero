# ACERO — Proactividad: novedad (anti-Erdősgate) · verificación formal · barrido masivo

Tres capacidades que salen del análisis del episodio "GPT-5 resolvió 10 Erdős":
la potencia estuvo en fan-out + verificación formal; el fallo, en confundir
*recuperación* con *descubrimiento*. ACERO toma la potencia y blinda el fallo.

## C — Checador de novedad (anti-Erdősgate) · `discovery/novelty_check.py`
Antes de gastar cómputo, busca en literatura REAL (OpenAlex, inyectable) si la
afirmación ya está resuelta; un LLM juzga si un paper la resuelve. Devuelve
`already_resolved | likely_open | uncertain` + `recovery_risk` + papers + recomendación.
Reglas: "no encontrado" NO prueba novedad (techo = `likely_open`); un paper que la
resuelve → `already_resolved` (es recuperación, no descubrimiento); sin búsqueda →
`uncertain`, nunca luz verde. Endpoint `POST /api/novelty-check`.

## B — Verificador formal simbólico · `science/formal_verify.py`
Con **sympy**: `identity | inequality | limit | boolean` → `proved | refuted | unknown`
(+ contraejemplo). Prueba real para lo que sympy decide; `unknown` es honesto y de
primera clase. Nivel de evidencia por encima de "reproducible" (como Lean en el único
caso IA autónomo real). Backend pluggable (Lean futuro). `POST /api/formal-verify`.

## A — Barrido masivo paralelo · `portal/sweep.py`
Genera N hipótesis y las filtra EN PARALELO por novedad(C) + EVA antes de gastar
cómputo; rankea sobrevivientes por (headroom de novedad × EVA-clean). Potencia
generativa estilo GPT-5, pero cada candidata pasa los mismos gates de honestidad;
nada se llama descubrimiento. `POST /api/projects/{id}/sweep {n, focus, enqueue}`
(con enqueue: aprueba y lanza misiones de los sobrevivientes).

Tests: `test_novelty_check.py` (5), `test_formal_verify.py` (9), `test_sweep.py` (5).
