# ACERO — Modo Experimento Agéntico

Todo lo que ACERO hacía con Codex ahora lo hace también con Claude, y el rol
**experimento** puede correr en **modo agéntico**: el agente (Claude Code)
**escribe, ejecuta, depura e itera** el script de análisis él mismo — pero
**obedeciendo las reglas del programa**. ACERO sigue siendo el sandbox
especializado que pone los pasos, la constitución y la validación. El agente
tiene más poder, pero DENTRO del marco; no hace las cosas por su cuenta.

## Principio

> El agente ejecuta con poder a partir del contexto del programa. El programa
> manda y valida. La salida del LLM NUNCA es evidencia.

## Flujo (3 fases)

```
        AUTORÍA (con red)              PUNTUACIÓN (sin red)         AUDITORÍA
  ┌────────────────────────┐     ┌────────────────────────┐   ┌──────────────┐
  │ docker: acero-agent     │     │ docker: acero-agent     │   │ ACERO         │
  │ claude -p agéntico      │ ──▶ │ python -I  (net=none)   │──▶│ reproduce-    │
  │ Write/Bash/Read/Edit    │     │ re-corre analysis.py    │   │ check +       │
  │ data/ = SOLO-LECTURA    │     │ → RESULT_JSON puntuado  │   │ cross-check + │
  │ escribe analysis.py     │     │ (fuente de verdad)      │   │ constitución  │
  └────────────────────────┘     └────────────────────────┘   └──────────────┘
```

1. **Autoría (con red).** El agente corre en un contenedor `acero-agent:py312`
   (`infra/agent/Dockerfile`: python+node+claude+numpy/pandas/scipy) CON red —
   la necesita para su API. Monta `./data` **solo-lectura** (no puede alterar los
   datos preregistrados) y `/work` escribible. Recibe el contrato científico de
   ACERO (nulos, discriminador, `RESULT_JSON`) más el addendum agéntico. Escribe
   `analysis.py`, lo ejecuta, ve errores y lo corrige hasta que cumple. Escribe su
   resultado afirmado en `agent_result.json`.

2. **Puntuación (sin red).** ACERO **no confía** en lo que reporta el agente:
   re-ejecuta `analysis.py` en la **misma imagen** con `--network=none` (paridad
   de librerías, cero red). El `RESULT_JSON` de esa corrida es el **puntuado**
   (fuente de verdad). Cae al sandbox de subprocess si Docker no está disponible.

3. **Auditoría.**
   - **reproduce-check**: compara lo *afirmado* por el agente (`agent_result.json`)
     contra lo *puntuado* sin red. Si no reproduce ⇒ bandera de integridad
     (posible uso de red o datos extra durante la autoría). Se reporta SIEMPRE el
     resultado sin red.
   - **cross-check**: un `supports` exige una segunda implementación independiente
     (constitución). Si no coinciden las métricas comparables ⇒ se degrada a
     `inconclusive`.
   - El techo sigue siendo **revisión humana**: el código es escrito por IA y es
     candidato, nunca descubrimiento. La automejora afina PARÁMETROS, no código.

## Configuración

| Variable | Default | Qué hace |
|---|---|---|
| `ACERO_EXPERIMENT_AGENT` | `1` | Activa el modo agéntico (`0` = generador por completion). |
| `ACERO_AGENT_IMAGE` | `acero-agent:py312` | Imagen de autoría + puntuación. |
| `ACERO_AGENT_TIMEOUT` | `3600` | Segundos máx. de una sesión agéntica (solo corta cuelgues reales). |
| `ACERO_CLAUDE_HOME` | `$HOME` | Dónde están las credenciales de Claude a montar. |

Construir la imagen una vez: `infra/agent/build.sh`.

Si el contenedor o las credenciales no están disponibles, `agent_available()` es
falso y la fábrica **cae automáticamente** al codegen por completion (que a su vez
usa el fallback Codex→Claude ya existente). Nada se bloquea.

## Auth dentro del contenedor

El CLI necesita `~/.claude/.credentials.json` (OAuth) **y** `~/.claude.json`
(`oauthAccount`). ACERO los copia a un HOME por-corrida (borrado al terminar) y
corre `docker run --user $(id -u):$(id -g)` para que el usuario del contenedor
pueda leer los `0600`. Sin esto: *"Not logged in"*.

## Archivos

- `src/acero/sandbox/agentic_runner.py` — `AgenticAuthor` (autoría enjaulada,
  runner inyectable), `agent_available()`.
- `src/acero/portal/experiment_factory.py` — `build_agentic_prompt`,
  `experiment_agent_enabled`, integración en `run_generated` (puntuación sin-red
  + reproduce-check).
- `infra/agent/` — `Dockerfile` + `build.sh`.
- `tests/unit/test_agentic_experiment.py` — offline (docker/claude inyectados).
