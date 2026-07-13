# ACERO — Auditoría del Entorno

**Fecha de auditoría:** 2026-07-12
**Host:** `Acero` (Linux)
**Método:** Inspección directa (`uname`, `lscpu`, `free`, `df`, `lspci`, `python3`, `node`, `docker`, `git`, `ollama`).
**Regla aplicada:** No se inventan capacidades. Solo se registra lo observado.

## 1. Sistema operativo
- **Kernel:** Linux 6.17.0-35-generic (`#35~24.04.1-Ubuntu`, PREEMPT_DYNAMIC)
- **Distribución base:** Ubuntu 24.04
- **Arquitectura:** x86_64

## 2. CPU
- **Núcleos lógicos:** 32
- **NUMA:** nodo único (CPUs 0-31)
- **Fabricante:** AMD (host bridges familia 19h)

## 3. Memoria
- **RAM total:** 62 GiB
- **Disponible (momento de auditoría):** ~39 GiB

## 4. GPU
- **Discreta:** NVIDIA (PCI `01:00.0`, device `2d59`) + audio HDMI asociado.
- **Integrada:** AMD Raphael (`69:00.0`).
- **`nvidia-smi`:** no disponible en el shell del sandbox → **VRAM no verificable en esta sesión**. No se asume disponibilidad de cómputo GPU para ACERO; todos los pilotos se diseñan para CPU.

## 5. Almacenamiento
- **Disco raíz:** `/dev/nvme0n1p2`, 937 GB total, ~275 GB libres (70% usado).
- **Espacio suficiente** para corpus pequeños, artefactos y bases SQLite/DuckDB locales.

## 6. Toolchain
| Herramienta | Versión | Estado |
|---|---|---|
| Python | 3.12.3 (`/usr/bin/python3`) | ✅ objetivo del stack |
| pip | 24.0 | ✅ |
| venv | disponible | ✅ |
| Node.js | 22.22.3 | ✅ (frontend futuro) |
| npm | 10.9.8 | ✅ |
| Docker | 29.1.3 | ✅ disponible (daemon activo) |
| git | 2.43.0 | ✅ |
| make | GNU Make 4.3 | ✅ |
| Ollama | 0.12.11 (cliente) | ⚠️ instalado, **daemon no activo**, sin modelos cargados |
| uv | — | ❌ no instalado (se usa venv+pip) |

## 7. Librerías Python (site-packages del sistema)
Ya disponibles (verificado con `importlib.util.find_spec`):
`numpy`, `scipy`, `pandas`, `sympy`, `scikit-learn`, `matplotlib`,
`fastapi`, `pydantic` (v2), `sqlalchemy`, `uvicorn`, `pytest`, `structlog`, `typer`, `httpx`.

**Faltantes:** `duckdb` (no crítico; se usa SQLite como almacén por defecto).

**Decisión:** el venv de ACERO se crea con `--system-site-packages` para reutilizar el stack científico ya instalado y evitar descargas masivas (política `large_downloads: false`).

## 8. Red
- **PyPI alcanzable** (`https://pypi.org/simple/` responde).
- Se respeta `policies/costs.yaml` y `policies/data_access.yaml`: no se descargan datasets masivos ni se activan servicios de pago.

## 9. Runtimes de IA local
- Ollama presente pero **sin servir** y **sin modelos**. → La capa LLM de ACERO se implementa con:
  1. `MockProvider` determinista (por defecto, usado en tests y esta sesión).
  2. `OllamaProvider` (adaptador listo; se activa solo si el daemon responde).
  3. Adaptadores `Claude`/`OpenAI` como **interfaces con guardas de costo** (deshabilitados por política).

## 10. Implicaciones de diseño
- **Local-first viable:** todo el ciclo Sprints 1–4 corre en CPU sin servicios de pago.
- **Sandbox:** Docker disponible → se ofrece backend Docker; con fallback a runner de subproceso restringido (`resource` + timeout + red desactivada por variables de entorno). Documentado en `docs/security/sandbox.md`.
- **GPU:** no se asume; reevaluar cuando `nvidia-smi` esté disponible.
- **Ollama:** reactivable con `ollama serve` + `ollama pull <modelo>` sin cambios de código.
