# Estándar de reproducibilidad de ACERO

Un tercero debe poder reejecutar cualquier experimento y obtener el mismo
resultado, o entender exactamente por qué no.

## Qué se registra por ejecución
- **Entorno** (`environment.json`): versión de Python, plataforma, arquitectura,
  implementación, marca de tiempo. Sin secretos.
- **Semillas**: toda fuente de aleatoriedad usa una semilla registrada
  (`ExecutionRun.seeds`). El piloto corre múltiples semillas.
- **Código**: el script exacto ejecutado (`code/script.py`) + su hash.
- **Inputs**: parámetros (`inputs/params.json`) + hash.
- **Outputs**: métricas y salidas + hash.
- **Hashes agregados**: `input_hash`, `code_hash`, `output_hash` (SHA-256).
- **Procedencia**: `provenance.json` enlaza prereg-hash, inputs, código, outputs.
- **Checksums**: `checksums.txt` con el hash de cada archivo del bundle.

## Verificación automática
El orquestador **reejecuta** la primera semilla y compara el hash del JSON de
salida. `reproduced = True` solo si coinciden. Prueba:
`tests/science/test_pilot.py::test_run_is_reproducible`.

## Determinismo
- `PYTHONHASHSEED=0` en el sandbox.
- RNG con semilla explícita (`numpy.random.default_rng(seed)`).
- IDs y timestamps se excluyen de los hashes de contenido cuando no forman parte
  del resultado científico (p. ej. `prereg_hash` excluye `registered_at`).

## Límites
- Diferencias de BLAS/versión de numpy entre máquinas pueden alterar los últimos
  dígitos; por eso se comparan resultados **dentro de la misma máquina/entorno**
  registrado. La comparación entre entornos distintos es trabajo de Sprint 11
  (robustez), y requiere tolerancias numéricas explícitas.
