# Sandbox de ejecución

Fuente: `src/acero/sandbox/` · Política: `policies/execution.yaml`

## Garantías (backend subproceso, POSIX)
1. **Screening estático previo** (`screen.py`): rechaza patrones prohibidos
   (`socket.`, `os.system`, `subprocess.Popen`, `urllib.request`, `eval(`, ...)
   antes de ejecutar. Estado resultante: `refused`.
2. **Aislamiento del intérprete**: `python -I` (ignora entorno y user-site).
3. **Sin secretos**: se construye un `env` mínimo (`PATH`, `HOME`, `TMPDIR`,
   `LANG`, `PYTHONHASHSEED=0`). `os.environ` del proceso padre **no** se propaga.
4. **Red deshabilitada**: se antepone un preámbulo que anula
   `socket.socket/create_connection`. Se usa preámbulo (no `sitecustomize`)
   porque `-I` ignora `PYTHONPATH`.
5. **Límites de recursos** (`preexec_fn`): `RLIMIT_CPU`, `RLIMIT_AS` (memoria),
   `RLIMIT_NPROC` (anti fork-bomb), `RLIMIT_CORE=0`, y `setsid` para matar el
   grupo de procesos.
6. **Timeout de pared**: mata el proceso; estado `timeout`, exit 124.
7. **Confinamiento de FS**: `cwd` = workspace del run; la política declara
   `filesystem: workspace_only`.
8. **Captura completa**: stdout, stderr, exit code, duración, y recorte a
   `max_output_bytes`.

## Estructura de artefactos por ejecución
```
<run_id>/
├── manifest.json      environment.json    provenance.json
├── metrics.json       result.md           checksums.txt
├── inputs/    code/    outputs/    logs/
```
Cada archivo se hashea (SHA-256) en `checksums.txt`; `inputs/`, `code/`, `outputs/`
se agregan en `input_hash`/`code_hash`/`output_hash` para el registro de la corrida.

## Backend Docker (implementado)
`sandbox/docker_runner.py` ejecuta el código en un contenedor endurecido:

```
docker run --rm --network=none --read-only
  --tmpfs /tmp:rw,size=64m
  --cap-drop=ALL --security-opt=no-new-privileges
  --pids-limit=128 --memory=<mb>m --memory-swap=<mb>m --cpus=<n>
  --user=<host uid:gid> -v <workspace>:/work:rw -w /work
  acero-sandbox:py312  python -I code/script.py
```

Ventajas frente al subproceso: **sin red a nivel de kernel** (no solo un guard),
raíz de solo lectura, capacidades caídas, sin escalada de privilegios, y sin
entorno del host (los secretos están ausentes por construcción). La imagen se
construye una vez con `infra/sandbox/build.sh` (incluye numpy, así el piloto corre
bajo Docker). `get_runner("docker")` devuelve este backend cuando Docker y la
imagen están disponibles; si no, hace fallback al subproceso (o lanza con
`strict=True`). Pruebas en `tests/security/test_docker_sandbox.py` (se saltan
limpiamente si Docker no está). Ver ADR-0002.

**Recomendado para código no confiable.** El backend subproceso sigue como
opción portátil por defecto.

## Cómo probarlo
`./.venv/bin/python -m pytest tests/security -q`
