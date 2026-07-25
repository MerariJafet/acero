# F12 — Caso científico en vivo end-to-end (12 fases)

Ejecución del prompt maestro completo. ACERO recibe un **tema general** (no una hipótesis
dada) y lo convierte en una **prueba discriminante lista para investigar**, bajo la
Constitución. Todo determinista y probado.

## Entrada
Tema: *"permeabilidad molecular (ADME)"*. Afirmación reconstruida:
"mayor polaridad (O+N) → menor permeabilidad Caco-2", evidencia observacional, una sola
raíz de procedencia (TDC), replicación solo interna (holdout).

## Recorrido de las 12 fases

| Fase | Salida real |
|---|---|
| F1 Reconstrucción | `ClaimRecord` con población/exposición/outcome/evidencia/replicación/raíces |
| F2 Lineaje evidencia | 1 sola línea independiente (comparte raíz TDC) |
| F3 EVA | 6 vulnerabilidades: `dependencia_fuente`, `resultado_no_replicado`, `confusion`, `mecanismo_ambiguo`, `extrapolacion`, `causalidad_inversa` — las mismas que el panel de 8 voces |
| F4 Preguntas | 6 preguntas vinculadas a vulnerabilidades, cartera diversificada por familia |
| F5 Control de calidad | gate multidimensional (bloquea no-falsables/triviales) |
| F6 Rivales | principal + nula + rivales (peso molecular, lipofilia) con predicciones diferenciales |
| F7 Prueba discriminante | **2.0 bits** de información esperada; decisiva (separa 4 resultados) |
| F8 Integración | pipeline avanza pre_research_states → `READY_FOR_EXPLORATORY_RESEARCH` |
| F9 Grafo de conocimiento | nodos Claim/Assumption/Evidence/Vulnerability/Question + relaciones, versionado |
| F10/F11 Benchmark | split evaluación: recall 1.0, falsos señalamientos 0, preguntas útiles 1.0 |
| F12 Caso en vivo | este documento |

## Pregunta top (priorizada, no por "qué tan llamativa suena")
**Transportabilidad** (`vuln caco2.src`): *"¿El efecto negativa entre polaridad y
permeabilidad se reproduce en una fuente de raíz de curación INDEPENDIENTE?"* → activa
`replication_finder` (Zenodo/ChEMBL) → cierra el hecho #4 pendiente.

## Enlace con la Constitución
La prueba discriminante entra al **régimen exploratorio**; para afirmar algo confirmatorio
debe pasar por protocolo congelado + holdout sellado + panel plural + claim compiler. El
sistema **no puede saltar** de un tema a un experimento confirmatorio.

## CLI
`acero science pipeline | qbench | eva | ask`

## Honestidad (veredicto permitido)
Estado: **LISTA_PARA_EVALUACIÓN_EXTERNA** de la capacidad de preguntas.
- Es maquinaria implementada y probada INTERNAMENTE (benchmark con splits dev/calib/eval),
  NO validada externamente.
- Falta: evaluación por expertos humanos de las preguntas (originalidad/relevancia/
  factibilidad), EVA con LLM sobre literatura real en dos modos, y el caso de frontera
  sobre datos reales end-to-end con réplica independiente.
- No se afirma "máquina autónoma de descubrimiento validada" ni "genera conocimiento
  verdadero". El techo sigue siendo la revisión humana.
