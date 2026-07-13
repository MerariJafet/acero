# ADR-0002: Sandbox por subproceso restringido como backend por defecto

- **Estado:** Aceptado
- **Fecha:** 2026-07-12

## Contexto
El Sprint 4 requiere ejecutar código Python de experimentos de forma segura.
Docker está disponible en el host, pero un backend de subproceso es más portable
y probable de funcionar en cualquier entorno de desarrollo.

## Decisión
Backend por defecto = **subproceso restringido**:
- Screening estático previo (`sandbox/screen.py`) rechaza patrones peligrosos.
- Ejecución con `python -I` (aislado), `env` mínimo sin secretos, `cwd` = workspace.
- Bloqueo de red en tiempo de ejecución mediante un preámbulo inyectado (porque
  `-I` ignora `PYTHONPATH`, no se puede usar `sitecustomize`).
- Límites de CPU (`RLIMIT_CPU`), memoria (`RLIMIT_AS`), procesos (`RLIMIT_NPROC`),
  y `setsid` para poder matar el grupo de procesos.
- Timeout de pared que mata el proceso.

**Actualización (post-Sprint 4):** el backend **Docker** está ahora
**implementado y probado** (`sandbox/docker_runner.py`, imagen
`acero-sandbox:py312`) con `--network=none --read-only --cap-drop=ALL
--security-opt=no-new-privileges --pids-limit --memory --cpus --user`. El
subproceso sigue siendo el **default portátil**; Docker se selecciona con
`ACERO_SANDBOX_BACKEND=docker` y es el recomendado para código no confiable.

## Consecuencias
- (+) Portable por defecto (subproceso), sin dependencia de daemon; probado.
- (+) Opción de aislamiento fuerte (Docker) disponible: red bloqueada a nivel de
  kernel, FS de solo lectura, capacidades caídas, sin entorno del host.
- (+) Defensa en profundidad: screening + aislamiento + límites de recursos.
- (−) Docker sigue por debajo de gVisor/nsjail en aislamiento; para adversarios
  fuertes, considerar esos backends (extensión futura). El `--user` con uid del
  host permite escribir el bind mount pero acopla el contenedor al uid del host.
