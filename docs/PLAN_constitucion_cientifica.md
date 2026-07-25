# Plan — Constitución Científica Computable (CCC)
### Respuesta de ingeniería a la crítica externa del especialista

**Diagnóstico del revisor (7.4/10):** la ingeniería está más madura que la validación
científica. El salto no es "más fuentes/agentes/modelos" sino una **constitución
científica computable** que gobierne: qué vio el sistema, cuándo, qué decidió antes de
ver resultados, cuántas rutas exploró, qué evidencia quedó independiente, qué afirmación
está permitida, y qué falsaría la hipótesis.

**Fórmula objetivo:** *Descubrimiento libre + confirmación bloqueada + causalidad
explícita + replicación independiente + trazabilidad completa.*

**Invariante que NO se rompe:** la separación razonamiento↔evidencia, la procedencia con
hash, los negativos preservados, el techo en revisión humana. Todo lo nuevo es
**aditivo** en un paquete nuevo `src/acero/science/` y se integra sin tocar el flujo que
ya funciona.

---

## Fase 0 — Indispensable (Prioridad 0 del revisor)

- **CCC-1 Pre-registro y régimen A/B** — `preregistration.py`. FrozenAnalysisPlan +
  ProtocolHash inmutable + UnblindingEvent + DeviationLog. El hash del protocolo
  (hipótesis, variable primaria, población, criterios, transformación, modelo, prueba,
  corrección por multiplicidad, tamaño mínimo del efecto, regla de decisión, condiciones
  de fracaso) debe existir **antes** de tocar datos confirmatorios.
- **CCC-2 Search Space Ledger** — `search_ledger.py`. Contabiliza TODO el espacio
  explorado por la misión completa (no solo un script) y calcula la *deuda de
  exploración*. Regla por código: todo resultado tras ver datos es exploratorio salvo
  que sobreviva a un protocolo confirmatorio congelado sobre evidencia nueva.
- **CCC-3 Holdout manager** — `holdout.py`. Split determinista discovery/holdout
  bloqueado por hash; se abre solo con UnblindingEvent. Aleatorio, temporal y por grupo.
- **CCC-4 Capa causal (CAUSA)** — `causal.py`. Estimando + DAG + criterio backdoor +
  identificabilidad + colisionadores/mediadores. Si no es identificable → prohíbe
  lenguaje causal.
- **CCC-5 Independencia + Claim Compiler** — `independence.py` (niveles 0–6) +
  `claim_compiler.py` (evidencia→afirmación máxima permitida; caza sobre-afirmaciones).

## Fase 1 — Poder científico (Prioridad 1)

- **CCC-6 Catálogo de nulos** — `nulls.py`. Familias que preservan estructura
  (etiquetas, bloque, sujeto, temporal, marginal/autocorrelación) con justificación
  obligatoria; el nulo genérico ya no basta.
- **CCC-7 Simulation & Recovery Bench** — `simbench.py`. Universos sintéticos con verdad
  conocida; mide FPR/FNR/sesgo/cobertura/potencia/recuperación de mecanismo. Una
  metodología no se usa para descubrir hasta pasar el bench.
- **CCC-8 Novedad (4 tipos) + ContributionScore** — `contribution.py`. Bibliográfica /
  datos / metodológica / científica; contribución = novelty × evidence × importance ×
  robustness × mechanism.
- **CCC-9 Presupuesto de incertidumbre** — `uncertainty_budget.py`. Multidimensional, no
  un solo número.

## Fase 2 — Gobierno

- **CCC-10 Panel adversarial plural** — `panel.py`. 8 revisores con mandatos
  incompatibles; preserva el desacuerdo.
- **CCC-11 Máquina de estados + orquestador** — `states.py` + `constitution.py`. Escalera
  IDEA→…→CANDIDATO_A_PREPRINT (techo ACERO) y checklist de controles estadísticos.
- **CCC-12 Integración + doc + verify + autoevaluación** honesta contra las 11
  dimensiones del revisor.

## Método de ejecución
Cada paso: implementar → tests unitarios deterministas → correr → si pasa mi evaluación,
siguiente. `make verify` verde al final de cada fase. Sin romper los ~950 tests actuales.
