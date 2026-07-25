# Constitución Científica Computable (CCC)

Paquete `src/acero/science/`. Responde a la crítica externa (7.4/10): *"la ingeniería está
más madura que la validación científica"*. Da la maquinaria para probar que un resultado
novedoso no surgió por exploración oportunista, confusión, fuga o autoengaño.

**Fórmula:** descubrimiento libre + confirmación bloqueada + causalidad explícita +
independencia real + trazabilidad total. Todo es **aditivo**: no altera el flujo existente.

## Módulos

| Módulo | Qué gobierna |
|---|---|
| `preregistration.py` | Régimen DISCOVERY/CONFIRMATION. Plan congelado + hash sobre el contenido científico (detecta ediciones post-hoc). Prohíbe revelar datos confirmatorios sin protocolo congelado. `UnblindingEvent`, `DeviationLog`. |
| `search_ledger.py` | Contabiliza TODO el espacio explorado (hipótesis/columnas/subsets/transformaciones/modelos/semillas/exclusiones). Comparaciones efectivas + deuda de exploración. Toda decisión tras ver datos = exploratoria por código. |
| `holdout.py` | Split determinista (aleatorio/temporal/por grupo) con holdout SELLADO hasta un `UnblindingEvent`. Split por grupo sin fuga de entidad. |
| `causal.py` (CAUSA) | DAG + criterio back-door vía d-separación + `Estimando` explícito + colisionadores/mediadores. Si no es identificable → bloquea lenguaje causal. |
| `independence.py` | Niveles 0–6. Una 2ª implementación NO es independencia. Afirmación fuerte = método distinto **y** dataset independiente. |
| `claim_compiler.py` | Evidencia → afirmación máxima permitida (asociado/predice/efecto-bajo-supuestos/replicado). LINTEA sobreafirmaciones (`demuestra/confirma/causa/descubrimiento`). |
| `nulls.py` | Catálogo de nulos que preservan estructura + recomendador que avisa cuándo la permutación simple infla los falsos positivos. |
| `simbench.py` | Universos sintéticos con verdad conocida. Mide FPR/potencia/sesgo y destapa confusión/lote/leakage. Una metodología no descubre hasta pasar el bench. |
| `contribution.py` | 4 tipos de novedad (la científica domina); "no encontrado" ≠ "nuevo". ContributionScore = novelty × evidencia × importancia × robustez × mecanismo. |
| `uncertainty_budget.py` | Presupuesto multidimensional (9 fuentes). El desglose es el resultado; el combinado es un piso. |
| `panel.py` | 8 revisores con mandatos incompatibles. Preserva el desacuerdo. Los mandatos duros (estadístico/causalista/detective) BLOQUEAN. |
| `states.py` | Escalera IDEA→…→CANDIDATO_A_PREPRINT (**tope ACERO**)→estados externos. |
| `constitution.py` | Orquestador: regime + claim permitido + sobreafirmaciones + estado + controles estadísticos → decisión ADVANCE/HOLD con razones. |

## CLI
```
acero science states     # escalera + tope ACERO
acero science simbench   # bench de recuperación sobre el t-test de referencia
acero science demo       # gobierna un resultado de juguete (caza sobreafirmaciones)
```

## Techo invariante
ACERO automatiza hasta `CANDIDATO_A_PREPRINT`. Los estados posteriores (revisión por
pares, publicado, replicado externamente) solo los mueven agentes externos humanos.

## Pendiente (siguiente pasada, requiere corridas reales)
Integrar la constitución dentro del Motor de Misiones y la síntesis del dossier (registrar
el search-ledger durante una misión real, congelar el protocolo antes del holdout, correr
el panel plural vía Codex, adjuntar el GovernanceReport al dossier). La maquinaria está
construida y probada; el cableado en vivo es una fase aparte para no arriesgar la suite.
