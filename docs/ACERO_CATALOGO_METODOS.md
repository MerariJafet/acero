# ACERO — MethodCatalog: las piezas de LEGO que el PROGRAMA posee

> "¿Le hemos dado una librería matemática actualizada que pueda usar como piezas de
> LEGO, o es solo deducción propia de su tabla de pesos? … quiero fortalecer algo
> superior con lo construido a su alrededor, no cargar todo a un solo sistema —
> porque entonces sería mejor hablar directo con el chat." — Merari

## El problema que resuelve

Antes, el Explorador elegía **métodos** desde el conocimiento paramétrico del LLM (su
"tabla de pesos"). Eso es: opaco (no se ve qué sabe), no auditable, y **no acumulable**
(el programa no se hacía más capaz; solo dependía del modelo). Si toda la creatividad
vive en los pesos, casi da igual chatear con el modelo directo.

`MethodCatalog` mueve ese "qué método" a **algo que ACERO posee**: un catálogo curado,
versionable y que **crece**.

## Qué es una pieza

Cada `Technique` tiene: `id · nombre · tags · para qué sirve · cómo funciona · idiom de
código (numpy/sympy/scipy/mpmath) · cuándo aplicarla`. Ejemplos del catálogo semilla
(20 piezas):

- `sym_sum` — sumatoria simbólica (`sympy.summation`) → formas cerradas de Σ.
- `nsimplify_identify` — **reconocer que `1.6449…` ES `π²/6`** (`sympy.nsimplify`).
- `char_equation` — recurrencias lineales → forma cerrada (Binet).
- `series_accel` / `high_precision` — series/productos lentos (Wallis, Euler-Mascheroni).
- `vandermonde_det`, `generating_function`, `telescoping`, `montecarlo_area`, …

Estas incluyen piezas que un chat plano **no invoca solo** — reconocimiento de
constantes, aceleración de series, alta precisión.

## Cómo cambia el reparto de trabajo

```
             ANTES                          AHORA
  qué método → pesos del LLM       qué método → CATÁLOGO del programa (retrieval)
  ejecución  → programa            ejecución  → programa
  verificación → programa         verificación → programa (+ sumatorias/productos)
  honestidad → programa            honestidad → programa
```

- **La recuperación la hace el PROGRAMA, no otra llamada al LLM**: `retrieve(goal)`
  puntúa las piezas por solapamiento de tokens/tags con el objetivo (lógica
  determinista) y ofrece una caja de ~8 piezas. Reproducible y auditable.
- Al LLM se le da esa caja concreta y su tarea pasa de *"recordá un método"* a
  *"ensamblá con ESTAS piezas"*. Registra `tools_used` por enfoque → **procedencia**.
- `learn(pieza)` agrega piezas nuevas y **persiste** (`acero_data/method_catalog/
  learned.json`). Cuando el sistema descubre un camino, el **programa** acumula
  capacidad — no los pesos del modelo.

## Verificación más fuerte (efecto colateral)

Al medir los primeros problemas vimos que el sistema hallaba la fórmula correcta pero
se quedaba en `holds_empirically` porque `formal_verify` no sabía probar **sumatorias**.
Se añadieron los kinds `summation` y `product` (vía `sympy.summation`/`product`): ahora
`Σk = n(n+1)/2`, `Σk² = n(n+1)(2n+1)/6`, `Σk³`, `Πk = n!` se **PRUEBAN** (`verified`),
y una forma cerrada equivocada se **refuta** con el `n` que discrepa. Eso es el programa
haciéndose más fuerte, no el LLM.

## Archivos

- `src/acero/science/method_catalog.py` — `MethodCatalog`, `Technique`, retrieval + learn.
- `src/acero/science/math_explorer.py` — inyecta la caja en diverge/assemble, registra `tools_used`.
- `src/acero/science/formal_verify.py` — kinds `summation`/`product`.
- `tests/unit/test_method_catalog.py`, `test_formal_verify.py`, `test_math_explorer.py`.
