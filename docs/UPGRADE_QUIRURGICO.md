# Upgrade quirúrgico — respuesta a la revisión externa (10-ago-2026)

El revisor calificó a ACERO 8.2/10: "muy buen sistema operativo de investigación
autónoma; todavía no una máquina madura de descubrimiento". Diagnóstico aceptado.
Este documento registra el triage de sus ~23 recomendaciones y qué se hizo HOY.

## Hallazgo del triage (importante)

Varias piezas que el revisor pide **ya existían en el código pero desconectadas
del flujo del Consejo** — el upgrade fue tanto conectar como construir:
`discovery/information_gain.py` (valor informativo), `inference/active_experiments/
discriminating.py` (experimentos discriminantes entre rivales — su punto 6),
`inference/discovery/invariants.py` (invariantes — su punto E), `symbolic_search`,
`change_points`, `sparse_identification`, `discovery/confidence.py`,
`program/budget.py`. La lección arquitectónica es del revisor: capacidades tipadas
evitan exactamente este "existe pero nadie lo sabe".

## Hecho HOY (commiteado, con tests)

| # revisor | Recomendación | Implementación |
|---|---|---|
| 4-5 | **Bohr híbrido**: LLM propone, máquina elige | `science/policy.py`: Bohr propone 2-4 candidatas (PROPOSE_SCHEMA estricto); PolicyEngine puntúa U = 1.5·info + 1.0·falsif + 0.8·novedad + 0.7·incert − costo − 1.2·riesgo − repetición. Costo/riesgo por tabla; **repetición MEDIDA en el historial** (no declarada). Desglose auditable en cada `decision` del ledger. Compatible con proveedores de decisión única (fallback limpio). |
| 3 | Personas = interfaz, no arquitectura | `science/capabilities.py`: PERSONA→CAPABILITY→TOOL→EVIDENCE tipado, con `llm_level` por capacidad (0=mecánica pura … 2=el juicio es el producto). `validate_registry()` en CI: sin capacidades huérfanas ni fantasmas. |
| 7 | Permisos de estado a nivel de tipos | `science/permissions.py`: KIND_WRITERS (Noether jamás escribe lemas; cada kind tiene dueños) + regla dura: `lemma.proved=True` exige backend MECÁNICO o se **degrada** a False con marca `_permiso_violado` (nunca se pierde información, nunca se eleva de más). Aplicado en `record_lemma`. |
| 9-D | Information-Theoretic Discovery | `MutualInfoDiscoverer` en patterns.py: MI normalizada por histograma — detecta dependencias en V/U/regímenes que Pearson no ve (test: y=\|x\| con r≈0). Solo reporta lo que la correlación NO explica ya. |
| 9-F | Sequence Discovery | `SequenceDiscoverer`: recurrencias lineales verificadas término a término, polinomios por diferencias finitas exactas, periodicidad modular. Una regla generadora comprime más que un ajuste. Directo al caso cover(N). |
| 19 | Incertidumbre explícita | `science/credence.py`: resumen MECÁNICO del ledger que distingue los 4 casos (sin evidencia / en contra / favorable débil / fuerte-pero-región-limitada), con dominio probado y fórmula a la vista (heurística DECLARADA como heurística). Anexado al informe de cada ciclo. |
| 13 | Regla del 90% → dos niveles | cover_growth: SOFT 80% (pausa despacho) / HARD 88% (drena hasta bajar del soft). El presupuesto-antes-de-lanzar queda para el scheduler (roadmap, con `program/budget.py` como base). |
| 14 | GPU por política, no por permiso-cada-vez | `gpu.py::GPU_POLICY` + `policy_allows(job)`: Merari aprueba la caja UNA vez (librerías, VRAM, duración, sin red); dentro de ella autonomía; salir de ella = humano. Cerrada hasta que active el driver. |
| 10 | GNN solo si gana un benchmark | Ya era la postura; ratificada. |
| 20 | Search Space Ledger | Ya existía; ratificado y conectado al score de evidencia como dirección. |

## Roadmap con criterio de entrada (tareas #123, #128)

| # revisor | Pieza | Criterio de entrada |
|---|---|---|
| 6 | **Experimental Design Engine** (discriminar H1..H4 por divergencia de predicciones) | conectar `inference/active_experiments/discriminating.py` + `information_gain` como jugada 'davinci' de Bohr — siguiente sprint |
| 11 | **Lean** como 4º verificador (proof objects) | cuando un lema del cover sobreviva Noether + reconciliación — no antes |
| 15 | **Artifact store** content-addressed (parquet/zarr; SQLite solo metadata) | cuando cover_growth.json o los embeddings pasen de ~100 MB |
| 17 | **Representation Search Engine** (el mayor hueco según el revisor) | FeatureLab es el germen; se amplía con transformaciones dirigidas por MDL tras validar la fase 1 en la Ronda 5 |
| 18 | **Theory Generator** (modelos competidores con predicciones/supuestos/fallos) | tras el primer dictamen de ley de crecimiento — las teorías rivales compiten sobre datos reales, no de salón |
| 21 | **Research Genome** (minería de trayectorias del ledger = metaaprendizaje) | requiere volumen: >100 rondas registradas; los costos de PolicyEngine se recalibrarán de ahí |
| 9-G | **Program Synthesis** en Mendeleev (la ley como programa generador) | tras SequenceDiscoverer en producción |
| 22 | Reorganización en 6 capas | adoptada como MAPA CONCEPTUAL (documentada en la tesis); no se mueven módulos por churn — la capa de capacidades ya da la vista lógica |

## Lo que se rechazó (con razón dicha)

- **Quitar la confirmación humana de GPU ya mismo**: se mantiene hasta que el
  driver esté activo y Merari apruebe la política — luego rige la caja.
- **Mover el ledger fuera de SQLite hoy**: correcto para el destino, prematuro
  ahora (el ledger actual es metadata liviana).
- **Bajar el techo HARD a 85%**: se fijó 88% — la workstation tiene 62 GB y el
  incidente real ocurrió por cachés sin tope, ya corregidas; 80/88 con drenaje
  es más conservador que el 90 plano anterior.
