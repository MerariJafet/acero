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

Se ofrece un backend Docker (`--network=none --read-only`) documentado; en esta
versión hace fallback a subproceso.

## Consecuencias
- (+) Portable, sin dependencia de daemon; probado en `tests/security/`.
- (+) Defensa en profundidad: screening + aislamiento de entorno + bloqueo de red.
- (−) Aislamiento más débil que un contenedor o gVisor/nsjail. Documentado como
  riesgo abierto; migrar a Docker/nsjail es trabajo de Sprint 7+ para código no
  confiable. Para el piloto (código propio, determinista) es suficiente.
