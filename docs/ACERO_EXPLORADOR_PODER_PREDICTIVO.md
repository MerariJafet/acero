# ACERO — Explorador matemático (poder predictivo)

> "No quiero que el programa se limite a *escuchar* una afirmación; quiero que
> *indague* en las posibilidades. Como obtener el área de un rectángulo: podría
> medirlas, buscar fórmulas y probarlas, usar derivadas… encontrar qué va
> funcionando y **por qué**. Creatividad para buscar otras opciones basándose en
> una librería matemática poderosa, como piezas de LEGO." — Merari

Este documento describe la capacidad que faltaba: la **mentalidad exploratoria**.
Hasta ahora ACERO era **reactivo** (le das una afirmación, la ataca). El
`MathExplorer` lo hace **proactivo**: le das un **OBJETIVO** y él piensa en
varios caminos, los prueba corriendo código, conserva los que funcionan, entiende
por qué, y de ahí saca una hipótesis que confronta.

## La diferencia

| | Entrada | Qué hace |
|---|---|---|
| `MathProbe` (reactivo) | una **afirmación** | busca contraejemplo / prueba formal |
| `MathExplorer` (proactivo) | un **objetivo** | genera enfoques → corre → sintetiza → confronta |

El explorador **usa** al probador como su paso final de confrontación. No lo
reemplaza; lo dirige hacia una hipótesis que él mismo descubrió.

## El bucle (piezas de LEGO)

```
OBJETIVO
 ├─ diverge     → propone K enfoques DISTINTOS
 │                (numérico · álgebra · cálculo · geometría · dimensional · patrón)
 ├─ arma+corre  → escribe UN script por enfoque (numpy/sympy/scipy = las piezas)
 │                y lo ejecuta en el sandbox SIN red, en paralelo
 ├─ selecciona  → conserva los enfoques VIABLES (found=true) y qué encontró cada uno
 ├─ sintetiza   → destila UNA hipótesis precisa + su forma formal (si se reduce)
 ├─ confronta   → MathProbe: refuted | verified | holds_empirically
 │                + NoveltyChecker: ¿ya está resuelto? (anti-Erdősgate)
 └─ si no queda cerrado → vuelve a divergir con lo aprendido
```

Cada enfoque es un **experimento computacional independiente** que corre en
paralelo (ThreadPoolExecutor). Los que fallan o no producen nada se descartan;
los que convergen alimentan la síntesis. Es exactamente el "deja scripts
corriendo, prueba teorías, quédate con las viables" que pediste.

## Honestidad heredada

El explorador no puede afirmar más de lo que el probador permite:

- `settled` **solo** si el probador dio `verified` (prueba formal sympy) o
  `refuted` (contraejemplo concreto).
- `candidate` si la hipótesis **aguanta empíricamente** pero no se probó — nunca
  se disfraza de demostración.
- La hipótesis pasa por el **checador de novedad**: si ya existe en la literatura,
  se etiqueta así. No revestimos un resultado conocido como nuevo.

## API

`POST /api/math-explore` (CSRF en el header)

```json
{ "goal": "encontrar la fórmula del área de un rectángulo de base b y altura h",
  "approaches": 4, "rounds": 2 }
```

Respuesta:

```json
{ "goal": "...", "status": "settled|candidate|inconclusive",
  "hypothesis": "área = b·h", "why": "los tres enfoques convergen…",
  "verdict": "verified", "verdict_detail": "…", "novelty": "already_resolved",
  "viable_approaches": [{"method": "numerico", "candidate": "b*h"}, …],
  "rounds": [{"round": 1, "approaches": 4, "viable": 3, "tried": [...]}] }
```

En el dashboard de proyecto: panel **⚡ Proactividad → 🧭 Explorador**.

## Por qué el ejemplo del rectángulo importa

No es que ACERO "no sepa" que el área es base×altura. El punto es la **mentalidad**:
partiendo solo del objetivo, el sistema *reconstruye* el resultado por varios
caminos independientes (muestreo Monte Carlo del área, integral de una constante,
descomposición en celdas unitarias, límite de sumas de Riemann) y **verifica que
todos coinciden**. Esa capacidad de *converger desde múltiples ángulos* es la que,
apuntada a una pregunta abierta, produce hipótesis genuinas — no una sola corazonada.

## Archivos

- `src/acero/science/math_explorer.py` — el motor.
- `src/acero/portal/app.py` — endpoint `/api/math-explore`.
- `src/acero/portal/static/js/dashboard.js` — panel 🧭 Explorador.
- `tests/unit/test_math_explorer.py` — 6 tests offline (todo inyectable).
