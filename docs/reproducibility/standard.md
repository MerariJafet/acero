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

## Discovery Engine (Sprints 5–7)
- El **torneo** es determinista: mismo conjunto de candidatos → mismo ranking y
  Elo (`test_tournament_is_reproducible`).
- La **generación mock** es determinista; la generación Codex registra
  provider/model/params/tokens para trazabilidad (no bit-reproducible por ser un
  servicio externo).
- El **benchmark Hidden Dynamics** reejecuta una semilla y compara el hash del JSON
  de salida (`reproduced=True`), igual que el piloto del Sprint 4.
- La **búsqueda random** usa semilla explícita; el **scheduler** permite *resume*
  saltando tareas completadas.

## World Model (Sprint 8)
- Cada creencia guarda **historial versionado** (confianza antes/después, evento,
  fuente); su trayectoria es reconstruible.
- Cada cambio del grafo emite un evento de procedencia (CREATE/LINK/UPDATE/
  CONFIDENCE_UPDATE/PRUNE).
- El dato real (exoplanetas) registra URL TAP, licencia, referencia y **hash
  SHA-256** del CSV; el test de Kepler es determinista dado el CSV.

## Cognitive Discovery Engine (Sprints 8.5–8.7)
- El análisis dimensional y Buckingham-Pi son **deterministas y exactos** (racionales
  vía SymPy). La verificación de derivaciones (SymPy) es determinista.
- La transferencia predictiva de la analogía se **verifica en el sandbox** (resonancia)
  y es reproducible dado el script y los coeficientes.
- Las propuestas de Codex (conceptos/analogías/derivaciones) registran provider/model/
  tokens; no son bit-reproducibles (servicio externo) pero sí verificadas por reglas.

## Governing Structure Inference (Sprints 8.8–8.9)
- La identificación dispersa (STLSQ) es determinista dado los datos y el threshold; la
  estabilidad usa bootstrap con semilla fija.
- La estimación de derivadas registra método y regiones no confiables; el gate epistémico
  exige reproducibilidad.
- El dato real (SILSO) registra URL, licencia, referencia y **hash SHA-256**; el análisis
  (FFT/periodo) es determinista dado el CSV.

## Human Understanding + Global Gate (Sprint 9)
- El grader es **determinista** (cobertura de elementos + penalizaciones + anti-eco); mismo
  texto y rúbrica → mismo score. Las transiciones de estado son deterministas dada la
  evidencia.
- El gate epistémico global es **determinista** por regla; el resultado de una etapa es
  reproducible dado el artefacto. Codex es advisory y se registra aparte (no bit-reproducible).
- La persistencia (perfil, estados, evidencia, predicciones, historial) va por el ledger con
  procedencia, como los demás stores.

## Domain Labs + Inline Gate + Hybrid Grader (Sprint 10)
- Los benchmarks de dominio usan RNG con semilla explícita → deterministas dado el entorno.
  Los solvers registran método/paso/estabilidad/error.
- El gate in-line es determinista por regla; el resultado de una mutación protegida es
  reproducible dado el artefacto; los rechazos se registran.
- El grader determinista es reproducible dado texto y rúbrica; la capa semántica (Codex) se
  registra aparte (no bit-reproducible) y nunca cambia el resultado a dominio.

## Scientific Reliability (Sprint 11)
- El grafo de dependencia de evidencia, la calibración y el red team son deterministas dado
  el conjunto de entrada; el gauntlet reejecuta detectores deterministas.
- Los tokens de mutación son single-use y por-proceso (no sobreviven un reinicio, por
  diseño); el contexto de gate es async-safe (contextvars) y no cruza subprocesos.
- La recalibración registra split train/calibration/test y rechaza solapes (leakage).

## Human Review & Publication Preparation (Sprint 12)
- El expediente y su export son deterministas dado el contenido; cada export escribe
  manifest + checksums SHA-256 por archivo y una declaración de uso de IA.
- La aprobación humana lleva un hash del expediente exacto; reexportar un expediente
  modificado se bloquea (binding verificable).
- Todo export es local (`destination: local_only`, `auto_published: false`).

## Límites
- Diferencias de BLAS/versión de numpy entre máquinas pueden alterar los últimos
  dígitos; por eso se comparan resultados **dentro de la misma máquina/entorno**
  registrado. La comparación entre entornos distintos es trabajo de Sprint 11
  (robustez), y requiere tolerancias numéricas explícitas.
