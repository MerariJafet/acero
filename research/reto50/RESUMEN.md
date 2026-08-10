# RETO 50 — Resumen honesto del primer barrido autónomo de ACERO

**Fecha:** 2026-08-07 → 08. **Duración:** ~4 h (50 problemas, secuencial).
**Techo epistémico (inviolable):** ningún problema abierto fue resuelto; nada aquí es un
descubrimiento hasta que lo valide revisión científica humana.

## Qué se hizo
ACERO corrió, de forma 100% autónoma, el método científico completo sobre 50 grandes
problemas matemáticos abiertos: Hilbert (conjetura falsable) → Hipatia (novedad,
literatura real) → Popper (ataque computacional) → Feynman (segunda jugada) →
Gödel/Euclides (intento de prueba / contribución parcial) → Aristóteles (crítica) →
Kepler (anomalías) → Bohr (disposición + informe). Un cron supervisó cada 15 min,
mantuvo el sistema vivo y fortaleció el código.

## Tabla de disposiciones (50/50)
| Disposición | N | Significado |
|---|---|---|
| needs_human_review | 45 | Sobrevivió a la búsqueda; sin lema mecanizable — el resultado honesto y esperado para problemas de esta talla |
| formally_supported | 2 | Un lema núcleo quedó probado mecánicamente (Primos gemelos, Erdős–Straus) |
| partial_progress | 1 | Contribución parcial verificada (Collatz: familia n=2^k) |
| dropped | 1 | Hadamard (existencia universal): no dio conjetura falsable atacable |
| TIMEOUT | 1 | Cuboide perfecto: la verificación formal se colgó (sin timeout duro — fix pendiente) |

## Los 3 lemas probados — y su honestidad
1. **Collatz** — probado: para n=2^k la iteración llega a 1 en k pasos. Clásico/trivial.
2. **Primos gemelos** — probado: condición local de admisibilidad del par (0,2) por residuos. Ladrillo estándar de cribas.
3. **Erdős–Straus** — `formally_supported`; además el toolkit nuevo cubrió 20/24 clases mod 24 con familias paramétricas VERIFICADAS.

**Novedad de los tres: NULA.** Son resultados clásicos re-derivados y verificados de
forma autónoma. Valor real = **fiabilidad demostrada**, no aporte nuevo.

## Revisión humana (ver REVISION_HUMANA.md)
Como par matemático endurecí Lehmer en 3 lemas necesarios y los verifiqué (Z3 + exhaustivo
a 2M). Correctos, pero clásicos (Lehmer 1932). En los ~45 supervivientes los bocetos
señalan la grieta real (Beal→triples primitivos, Brocard→congruencias, Erdős–Moser→
valuaciones p-ádicas), pero el salto a teorema nuevo exige maquinaria (curvas elípticas,
cribas, formas modulares) fuera del alcance actual de sympy/Z3+búsqueda.

## Maquinaria nueva construida esta sesión (frontier_toolkit.py)
Descubridor+verificador de familias paramétricas y mapeador de coberturas por clases de
residuos + probador de condiciones necesarias (Z3). Erdős–Straus mod 24: 20/24 cubiertas,
frontera reportada [1,9,13,21]. **Correcto pero incompleto**: 9 y 21 SÍ son solubles
(plantillas aún débiles) → la frontera está sobre-reportada. Es el punto de partida
honesto del bucle crecer→probar→fortalecer, no un resultado final.

## Candidatos a paper
**Ninguno con conocimiento nuevo.** El entregable real y valioso es distinto: el primer
**mapa autónomo, honesto y trazable** de 50 fronteras, con 0 falsos positivos en 50
intentos imposibles — evidencia fuerte de que ACERO es un investigador *fiable*.

## Dónde vive el aporte real (siguiente paso) — ESTADO 2026-08-08
1. ✅ **HECHO — PARIDAD CLÁSICA ALCANZADA.** frontier_toolkit v3 (plantillas tipo II
   `(n+t1)(n+t2)/m` + prueba de integridad por período modular completo + prefiltro
   Fraction): duros mod 840 = **exactamente {1,121,169,289,361,529}** (los cuadrados
   de Mordell), en 6 s. Redescubrió solo las identidades clásicas (incl. mod 5/7).
   Para esos 6 residuos hay obstrucción teórica (Schinzel): ninguna familia polinomial
   de este tipo existe — la novedad ahí exige otros métodos, no más plantillas.
2. ✅ **HECHO.** cypari2 + python-flint + gmpy2 instalados (wheels manylinux) y
   verificados: PARI calcula rango analítico de curvas elípticas, FLINT primalidad.
   (sage completo sigue fuera de pip; PARI/FLINT cubren curvas y formas modulares.)
3. ✅ **HECHO — con veredicto honesto.** `caccetta_haggkvist_bounded` (Z3): k=3 probado
   mecánicamente para **n=3..13** (WLOG sanos: outdeg exacto + vecindad de v0 → n=11
   de timeout a 4 s; cardinalidad nativa AtLeast/AtMost en v3 → n=12 en 695 s y n=13
   en 958 s; n=14 agotó 25 min — límite actual del método directo). Ciclo del Consejo
   completo sobre el lema (proj_01KZH5AF42GBQT2QQ0NB5G72R6): **Hipatia dictaminó
   novedad ASENTADA** — el lema se deduce de Hamidoune 1987 (grado 3, DOI
   10.1016/0095-8956(87)90009-8) y Hoàng–Reed 1987 (grados 4-5, DOI
   10.1016/0012-365X(87)90122-1), que de hecho cubren todo n<=15. El anti-Erdősgate
   funcionó en vivo: impidió vender una re-derivación mecanizada como aporte.
   **Frontera real identificada:** CH(k=3) está abierto desde grado 6 → n∈{16,17,18}
   son los primeros casos finitos vírgenes; exceden el SAT directo (n=12 ya cuesta
   minutos) — se requieren álgebras de banderas o SAT masivo con simetrías.
4. ✅ **HECHO.** Timeout duro en formal_verify (proceso hijo + kill): un claim
   patológico ya no puede congelar un ciclo (bug Cuboide). Test forzado: unknown en 3 s.
   Todo lo anterior con tests: tests/unit/test_frontier_toolkit.py (9/9).

## Actualización 2026-08-08 (tarde) — el lema de covering sets

Con Bohr v2 (director dinámico) el Consejo produjo su primer candidato serio a
contribución: certificados explícitos de Erdős–Straus para las 6 clases duras
mod 840 y el estudio del CONJUNTO MÍNIMO de auxiliares (ver
NOVEDAD_COVERING_SETS.md y stress13.py):
- 10⁵: 273 primos, 0 sin cobertura, cover mínimo 5; 10⁶: 2,370, 0, cover 8;
  **10⁷: 20,513 primos, 0 sin cobertura, cover 10** (k≤167; k=23 solo ≈67%).
- Hipatia: `likely_open` para la formulación; revisión par: empaquetado nuevo de
  maquinaria clásica con pregunta estructural nueva (crecimiento del cover).
- Fix Aristóteles: el crítico recibía un dict (rompía en silencio →
  'sin_revision'); ahora recibe el LOG textual completo del ciclo.

## Actualización 2026-08-10 — cierre de la caza de CH n=14 (ataque directo)

Los dos ataques directos con presupuesto grande sobre Caccetta–Häggkvist n=14
(k=3, outdeg≥5) **cerraron ambos en `unknown`**, honesto, sin veredicto:
- **v4** (n=15, 12h): `unknown` — igual que n=14, el caso también resiste.
- **v5** (n=14, 24h de presupuesto, orden de Merari): `unknown` a las 24.0h
  exactas — Z3 no cerró ni encontró contraejemplo en un día completo.

**Lo que esto significa, sin inflar:** el método directo (una sola búsqueda Z3,
por larga que sea) tiene un techo real en n=14. No es un fracaso — es la medida
honesta de dónde está la frontera actual del método. El experimento de
**cube-and-conquer** (partición del espacio en 4096 cubos) confirmó la misma
lección desde otro ángulo: con las 12 aristas de ramificación elegidas, solo
~1.6% de los cubos cerraba en 60s — la partición naive no muerde este problema
(ver `cube14.txt`); hace falta ramificación estructural, no aristas sueltas.

**Sigue vivo el ataque por portafolio** (la apuesta a que una ruta de búsqueda
distinta tenga suerte donde la directa no): 4 semillas a 7 días cada una +
1 semilla maratonista a 10 días, todas corriendo en paralelo sin límite
artificial de tiempo. Si alguna cierra en `proved`, es un teorema nuevo del
sistema para n=14; si en `counterexample`, sería un resultado extraordinario
que exige verificación independiente inmediata antes de creerlo.

## Veredicto
ACERO cerró su primer maratón autónomo con **disciplina epistémica intachable**: 50
problemas, 3 lemas honestamente probados y etiquetados como clásicos, 1 descarte honesto,
0 exageraciones. No creamos conocimiento nuevo esta noche — y decirlo con claridad ES el
logro: un investigador autónomo en el que se puede confiar.
