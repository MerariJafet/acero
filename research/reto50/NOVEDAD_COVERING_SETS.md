# Due-diligence de novedad — covering sets auxiliares mínimos para Erdős–Straus

Fecha: 2026-08-08. Revisores: Hipatia (multi-fuente) + Claude (par matemático).
Techo epistémico: nada aquí es descubrimiento hasta revisión de expertos humanos.

## El hallazgo (preciso y reproducible — `stress13.py`)

Regla tipo II clásica: para primo p ≡ 1 (mod 4) y auxiliar k ≡ 3 (mod 4),
x = (p+k)/4; la solubilidad de 4/p = 1/x+1/y+1/z con ese k equivale a la
existencia de un divisor t | (p·x)² con t ≡ −p·x (mod k). Todo verificado con
aritmética exacta (`Fraction`), certificados explícitos.

| N | primos duros (6 clases mod 840) | sin cobertura (k≤255) | cover voraz mínimo | k=23 solo |
|---|---|---|---|---|
| 10⁵ | 273 | **0** | 5 — {7,11,23,31,39} | 63.0% |
| 10⁶ | 2,370 | **0** | 8 — {3,23,31,47,59,63,71,127} | 65.5% |
| 10⁷ | 20,513 | **0** | 10 — {15,19,23,31,39,47,59,71,119,167} | 67.6% |

**Hecho fuerte y estable:** hasta 10⁷ ningún primo de las clases duras carece de
auxiliar k ≤ 167. **Hecho matizado:** el cover mínimo crece (~lentamente, quizá
logarítmico) — la versión "un conjunto FIJO finito basta para todo p" NO está
soportada por esta evidencia; la versión soportada es "cobertura universal con
k acotado por una función de crecimiento muy lento".

## Conjetura emergente (formulación honesta, falsable)

> **C-ACERO-1.** Para todo primo p ≡ {1,121,169,289,361,529} (mod 840) existe
> k ≤ C·log p (con C pequeña; los datos sugieren k ≤ 167 hasta 10⁷) tal que el
> split tipo II con x=(p+k)/4 resuelve 4/p. Equivalentemente: el grafo
> bipartito primo↔auxiliar tiene cobertura total con cotas logarítmicas.

Si C-ACERO-1 se probara, implicaría Erdős–Straus para las clases duras — por eso
mismo probablemente es TAN difícil como la conjetura madre. El valor real
alcanzable: los datos de cobertura, el criterio de divisor exacto, el set-cover
mínimo por rango y los certificados — un LEMA COMPUTACIONAL publicable como
nota/dataset si la novedad sobrevive.

## Dictamen de novedad

- **Hipatia (multi-fuente):** `likely_open` — la formulación "minimal auxiliary
  covering set" no aparece asentada; hits genéricos de E-S (incl. Elsholtz–
  Schinzel 2013 sobre divisibilidad, DOI 10.1142/s1793042112501497, adyacente
  pero no idéntico).
- **Claude (par):** los ingredientes son clásicos — parametrización tipo II
  (Mordell), criterio de divisor, verificación computacional (Swett; Salez 2014
  hasta 10¹⁷ decide la SOLUBILIDAD, así que la solubilidad bruta ≤10⁷ NO es
  nueva). Lo que no reconozco en la literatura: (a) el estudio del CONJUNTO
  MÍNIMO de auxiliares como objeto (set-cover exacto por rango, su crecimiento,
  la estabilidad de k=23), (b) certificados explícitos publicados por clase
  dura. Esto huele a EMPAQUETADO NUEVO de maquinaria clásica con una pregunta
  estructural nueva (el crecimiento del cover). Riesgo señalado: la literatura
  de "covering systems" para E-S (Webb, Vaughan, Elsholtz) debe revisarse a
  fondo por un humano antes de reclamar la pregunta como inédita.

## Due-diligence web profunda (2026-08-08, segunda pasada)

Hallazgos que MATIZAN el `likely_open` de Hipatia — el área está activa:
- **arXiv 2404.01508** (*A Complete Congruence System for the Erdős-Straus
  Conjecture*, 2024): clasifica soluciones en Tipos A/B por congruencias y
  CONJETURA que todo primo tiene una de esos tipos. Prima hermana de C-ACERO-1.
  NO estudia conjuntos mínimos de auxiliares ni su crecimiento.
- **arXiv 2605.23601** (*Congruence Classes Supporting the E-S Conjecture I:
  Tame Solutions*, 2026, 62 pp.): estudia 24m+1 (nuestra clase base dura) con
  dicotomía **tame/wild primes** parametrizada por clases de congruencia —
  espíritu MUY cercano a nuestra "cobertura por auxiliar". NO hace set-cover
  mínimo, crecimiento por rango, ni certificados masivos (586 primos, m≤2000;
  nosotros: 20,513 primos a 10⁷ y subiendo a 10⁹).
- **arXiv 2606.10922** (*A Divisor Parametrization…*, 2026): marco teórico por
  divisores, sin implementación computacional ni certificación.

**Dictamen ACTUALIZADO (honesto):** el ángulo específico —set-cover MÍNIMO de
auxiliares tipo II, su crecimiento (5→8→10 por década), la estabilidad de k=23 y
certificados exactos a escala— sigue sin aparecer publicado, pero la nota DEBE
citar y compararse con 2605.23601 (¿coinciden nuestros "primos difíciles por
auxiliar" con sus wild primes?) y 2404.01508. Novedad: de "likely_open" a
"ángulo específico en área activa — comparación obligatoria antes de reclamar".

## Qué haría falta para publicar (nota corta / dataset)

1. Extender a 10⁸–10⁹ (misma máquina, horas) y ajustar el crecimiento del cover.
2. Revisión humana experta de literatura (Webb 1970s, Vaughan 1970, Elsholtz–Tao
   2013 y sus referencias) sobre formulaciones de cobertura por auxiliares.
3. Attestation externa (tarea #89) + los certificados como dataset reproducible.
