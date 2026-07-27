# ACERO — Loop del Investigador Principal (PI)

El loop autónomo que cierra el ciclo: el agente **diseña → la máquina corre →
retro a un archivo → el agente despierta, lee y decide → repite**. Desacopla el
PENSAR del COMPUTAR: el agente solo está cargado unos segundos por *tick*; los
experimentos corren en la compu sin su contexto.

## Ciclo

```
   TICK (agente cargado ~segundos)                 COMPUTO (agente descargado)
  ┌───────────────────────────────┐              ┌────────────────────────────┐
  │ build_digest: estado compacto  │              │ Mission Engine por hipótesis│
  │  (hipótesis, veredictos,       │  encola      │ investigar→proponer→correr  │
  │   anomalías, rigor, decisiones)│ ───────────▶ │ (runner agéntico enjaulado) │
  │ PI decide (LLM, structured)    │              │ →sintetizar→loop de rigor   │
  │ metodología valida             │              └──────────────┬─────────────┘
  │ feedback.jsonl ◀───────────────┼─────────────────────────────┘
  └───────────────────────────────┘   al terminar misiones (o intervalo) → siguiente tick
```

## Decisiones del PI

Cada tick el PI elige UNA acción (validada por la metodología):

- `generate_and_run` — crea `n_new` hipótesis nuevas hacia un `focus` (usa el
  generador frontera de ACERO), las aprueba, y arranca misiones.
- `run_existing` — corre lo aprobado pendiente sin crear más.
- `deepen` — profundiza el rigor de lo ya corrido.
- `pause` — **cooldown, NO detiene el loop.** El PI solo puede declinar añadir
  trabajo ahora (fricción operativa, nada informativo): no arranca misiones, deja
  drenar las que corren, hace back-off y vuelve a tickear con el estado ya cambiado.
  Solo el investigador detiene el loop (`pause(pid)` / endpoint / botón).

Sin LLM disponible hay un fallback determinista (bootstrap → perseguir anomalías
→ correr pendientes) para que el loop nunca se cuelgue.

## La metodología manda (invariantes, no negociables)

- Cada acción se acota aquí (`_validate`: tope de hipótesis nuevas por tick,
  acción válida) y se gatea aguas abajo por la constitución: controles nulos,
  verificación cruzada independiente, novedad/independencia, floors de validez y
  especificidad.
- **Nada se promueve a descubrimiento sin revisión humana.** El loop propone,
  corre y revisa; jamás publica.
- Autonomía **ilimitada hasta que pauses**. Un tick seco (sin trabajo válido)
  hace back-off exponencial en vez de girar en caliente quemando tokens.

## Driver (evento + intervalo)

`ResearchLoop.run(pid)`: tick → espera a que terminen las misiones del proyecto
(poll de `list_missions`) **o** a que pase `interval_sec` → siguiente tick.
`start_background(pid)` lo corre en un hilo daemon.

## Estado y archivos

Bajo `research/loop/<project_id>/` (override `ACERO_LOOP_ROOT`):
- `state.json` — `{paused, ticks, dry_streak, status, started_at, last_tick_at}`.
- `feedback.jsonl` — una línea por tick (decisión + qué se aplicó + resumen del
  digest). Es la memoria del PI: el próximo tick lee las últimas entradas.

Controles: `pause(pid)`, `resume(pid)`, `is_paused(pid)`, `load_state(pid)`.

## Configuración

| Variable | Default | Qué hace |
|---|---|---|
| `ACERO_PI_INTERVAL_SEC` | `1800` | Intervalo máximo entre ticks si las misiones no terminan antes. |
| `ACERO_PI_MAX_NEW_HYP` | `4` | Tope de hipótesis nuevas por tick. |
| `ACERO_PI_BACKOFF_CAP_SEC` | `7200` | Techo del back-off en ticks secos. |
| `ACERO_LOOP_ROOT` | `research/loop` | Dónde viven `state.json` y `feedback.jsonl`. |

## Archivos

- `src/acero/portal/research_loop.py` — `PrincipalInvestigator` (digest, decide,
  validar, aplicar, tick), `ResearchLoop` (driver evento+intervalo), pausa/estado.
- `tests/unit/test_research_loop.py` — offline (provider y servicios inyectados).

Pendiente (Capa 2): vista en el dashboard (ticks, decisiones, misiones en curso,
veredictos; botones pausar/reanudar/avanzar-un-tick).
