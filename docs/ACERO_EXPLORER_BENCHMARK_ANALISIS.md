# Análisis honesto — Explorador ACERO: base vs. consolidado (10 problemas ya-demostrados)

Banco de 10 resultados matemáticos **probados** (respuesta conocida), corridos dos veces:
**BASE** (sin catálogo, verificador y guardas) y **MEJORADO** (una sola forma consolidada).
Todo computado en sandbox **sin red** — nada se buscó en internet.

## Tabla comparativa

| # | Problema | Respuesta | BASE | MEJORADO | ¿candidato correcto? |
|---|----------|-----------|------|----------|:--:|
| 1 | Suma de Gauss | n(n+1)/2 | holds_empirically | holds_empirically | ✅ |
| 2 | Suma de impares | n² | holds_empirically | holds_empirically | ✅ |
| 3 | Suma de cuadrados | n(n+1)(2n+1)/6 | holds_empirically | holds_empirically | ✅ |
| 4 | Suma de cubos | (n(n+1)/2)² | holds_empirically | **verified** ⬆ | ✅ |
| 5 | Serie geométrica | (rⁿ−1)/(r−1) | inconclusive | candidato ⚠ (refut. no corroborada) | ✅ |
| 6 | Basilea Σ1/n² | π²/6 | holds_empirically | candidato ⚠ (tail near-miss) | ✅ |
| 7 | Área del círculo | πr² | holds_empirically | holds_empirically (near-miss filtrado) | ✅ |
| 8 | Integral gaussiana | √π | **refuted (FALSO)** | **verified** ⬆⬆ | ✅ |
| 9 | Leibniz | π/4 | **refuted (FALSO)** | holds_empirically ⬆ | ✅ |
| 10 | Binet (Fibonacci) | (φⁿ−ψⁿ)/√5 | **refuted (FALSO)** | inconclusive ⬆ | ✅ |

## Marcador

| Métrica | BASE | MEJORADO |
|---|:--:|:--:|
| Fórmula/valor **correcto** hallado | 10/10 | 10/10 |
| Pruebas formales reales (`verified`) | 0 | **2** (#4, #8) |
| Refutaciones **FALSAS** decisivas (`settled`) | **3** | **0** |
| Casos degradados a revisión humana por guarda | 0 | 2 (#5, #6) |

## Puntos fuertes (qué hace bien)

1. **La mentalidad exploratoria funciona:** de solo el OBJETIVO, reconstruye la respuesta
   correcta **10/10**, cada una por ~4 caminos **independientes** que convergen
   (p.ej. gaussiana por coordenadas polares · función Gamma · integral paramétrica ·
   probabilidad). Sin red: es reconstrucción, no búsqueda.
2. **Verificación formal real:** #4 (Σk³) y #8 (∫e^{−x²}) pasan a `verified` por prueba
   simbólica en sympy — no "reprodujo", sino **demostrado**.
3. **Honestidad por construcción:** nada quedó como falso positivo decisivo.

## El hallazgo clave (Eureka en reversa)

El BASE **mentía**: declaró `refuted` (settled, decisivo) sobre **tres teoremas
verdaderos** (√π, π/4, Binet). Tres causas distintas:
- **#8**: el script usó una tolerancia numérica (5e-9) más estricta que su propia
  precisión de cuadratura (error 2.6e-6) → "contraejemplo" que era ruido de punto flotante.
- **#9**: un script con bug evaluó la serie en un punto degenerado (r=0).
- **#10**: una `formal_claim` mal codificada, refutada por sympy.

Un "refutado" falso es lo más peligroso que puede producir un sistema de descubrimiento.
La consolidación introdujo el principio **"refutar exige corroboración"**:
- `_robust_counterexample` descarta near-miss numéricos y colas de truncamiento.
- conflicto formal-vs-empírico (formal refuta pero la búsqueda no halla contraejemplo)
  ⇒ `inconclusive` (probable mal-codificado), nunca `refuted`.
- **guarda de consenso**: refutar lo que 2+ enfoques independientes sostienen ⇒ se
  degrada a `candidato` para revisión humana.

Resultado: **las 3 refutaciones falsas desaparecieron** (una incluso se volvió prueba real).

## Puntos débiles honestos (lo que falta endurecer)

1. **#1–#3 se quedan en `holds_empirically`** aunque el programa SÍ puede probarlas
   (lo demuestra #4 en vivo y los tests unitarios de `summation`). El sintetizador no
   codifica de forma **fiable** la `formal_claim` de sumatoria en cada caso — es un tema
   de compliance del LLM, no una capacidad ausente.
2. **El probador todavía GENERA refutaciones falsas** (#5, #6): las guardas las atrapan
   (→ candidato, no settled), pero idealmente no se generarían. La calidad del codegen
   que caza contraejemplos es el siguiente frente.

## Programa vs. LLM (lo que pediste vigilar)

Tras la consolidación, **más valor vive en el programa**, no en los pesos del modelo:

| Lo hace el **programa** | Lo hace el **LLM (CLI)** |
|---|---|
| Ofrece las piezas LEGO (catálogo, retrieval determinista) | Propone enfoques y escribe el código |
| Ejecuta sin red (obliga a computar) | — |
| Recuerda qué funcionó (ledger persistente) | — |
| **Prueba** sumatorias/identidades (sympy) | — |
| **Corrobora** antes de refutar (3 guardas) | — |
| Se abstiene y marca para revisión humana | — |

## ¿Vamos por buen camino?

**Sí.** La propiedad más importante de un sistema de descubrimiento —**no afirmar cosas
falsas de forma decisiva**— pasó de 3 fallos a 0, y aparecieron 2 pruebas formales reales,
manteniendo 10/10 en hallar la respuesta correcta. El "nuevo camino" genuino se probará
mejor contra un problema realmente abierto (siguiente paso), donde no exista solución que
"recordar".

## Reproducir

`POST /api/math-explore` con `{"goal": "...", "approaches": 4, "rounds": 2}` o el panel
**⚡ Proactividad → 🧭 Explorador**. Datos crudos:
`scratchpad/bench_results.jsonl` (base) y `bench_improved_results.jsonl` (mejorado).
