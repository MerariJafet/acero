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

## Backend Docker (documentado)
`get_runner("docker")` está previsto para ejecutar con
`docker run --network=none --read-only --memory ... --cpus ...` sobre una imagen
mínima. En esta versión hace fallback al subproceso (ver ADR-0002). Recomendado
para código no confiable.

## Cómo probarlo
`./.venv/bin/python -m pytest tests/security -q`
