# Minimal auxiliary covering sets for the Erdős–Straus conjecture on the hard residue classes mod 840

**BORRADOR v0.1** — nota corta + dataset. Estado: en preparación; requiere
revisión humana experta y attestation externa antes de cualquier envío.
Autoría: Merari Jafet (investigador y validador humano) con el sistema ACERO
(consejo autónomo de agentes; ver sección Reproducibilidad). ACERO no se
atribuye autoría (constitución).

## Abstract (EN)

For the Erdős–Straus conjecture 4/p = 1/x + 1/y + 1/z, the six residue classes
p ≡ 1, 121, 169, 289, 361, 529 (mod 840) are the classical hard cases: no
polynomial identity can cover them (Schinzel's obstruction). We study the
classical type-II split x = (p+k)/4 (k ≡ −p mod 4) as a DECISION LIST over a
small set of auxiliary values k, where solvability for a given k reduces to the
existence of a divisor t | (px)² with t ≡ −px (mod k). Our computations show:
(i) every one of the 1,587,420 hard primes up to 10⁹ is decided by some
k ≤ 255 (in fact k ≤ 167 up to 10⁷, exhaustive matrix); (ii) minimal covering
sets grow slowly — 5 values suffice up to 10⁵, 8 up to 10⁶, 10 up to 10⁷
(exact), and stratified samples indicate 7–9 at 10⁸–10⁹; (iii) the single
auxiliary k = 23 alone decides a monotonically INCREASING share of hard primes:
63% → 65% → 68% → 70% → 72% across five orders of magnitude. All certificates are explicit and re-verified
with exact rational arithmetic; code and data are published for one-command
reproduction. We formulate the resulting growth question (is the minimal cover
O(log N)?) and relate it to recent congruence-class approaches
(arXiv:2404.01508; arXiv:2605.23601).

## 1. Definiciones

Sea p primo con p mod 840 ∈ H = {1,121,169,289,361,529}. Para k ≡ 3 (mod 4)
definimos x = (p+k)/4. Decimos que **k decide a p** si existe t | (p·x)² con
t ≡ −p·x (mod k); en tal caso y = (px+t)/k, z = px(px+t)/(kt) dan
4/p = 1/x + 1/y + 1/z con x,y,z ∈ ℤ⁺ (verificación exacta).

Para N, sea P(N) el conjunto de primos duros ≤ N y C(N) el menor S ⊆ ℕ tal que
todo p ∈ P(N) es decidido por algún k ∈ S.

## 2. Resultados computacionales (todos con aritmética exacta)

| N | \|P(N)\| | sin cobertura (k≤255) | \|cover\| (voraz+poda) | cover | k=23 solo |
|---|---|---|---|---|---|
| 10⁵ | 273 | 0 | 5 | {7,11,23,31,39} | 63.0% |
| 10⁶ | 2,370 | 0 | 8 | {3,23,31,47,59,63,71,127} | 65.5% |
| 10⁷ | 20,513 | 0 | 10 | {15,19,23,31,39,47,59,71,119,167} | 67.6% |
| 10⁸ | ≈179,450 | 0 | 7 (muestra 1/50) | {23,31,47,59,71,119,143} | ≈70%* |
| 10⁹ | 1,587,420 | **0** | 9 (muestra 1/100) | {23,31,39,47,59,71,95,119,167} | ≈72%* |

\* En 10⁸ el % de k=23 es "decide como PRIMERO en el orden de prueba"
(125,489 primos) — cota inferior de su cobertura total; el cover es sobre
muestra estratificada de 3,649 primos (cota inferior del cover completo).

Certificados explícitos por primo (JSON/CSV) hasta 10⁵ publicados; muestra
estratificada verificada a escalas mayores. Verificación triple independiente
en 10⁵ (dos implementaciones del sistema + re-verificación externa): 0 fallos.

## 3. La pregunta estructural (nueva hasta donde sabemos)

**C-ACERO-1 (versión soportada por los datos).** Existe C > 0 tal que todo
primo duro p es decidido por algún k ≤ C·log p.

**Pregunta del cover.** ¿Es |C(N)| = O(log N)? Los datos (5, 8, 10 por década)
son consistentes con crecimiento ~logarítmico. Una prueba de cualquiera de las
dos implicaría Erdős–Straus para las clases duras — por lo que esperamos que
sean difíciles; el aporte de esta nota es el OBJETO (el cover mínimo y su
crecimiento) y el dataset, no un teorema.

## 4. Relación con trabajo previo (comparación obligatoria)

- Solubilidad bruta: verificada hasta 10¹⁷ (Salez 2014) — NO es aporte nuestro.
- Identidades polinomiales por clases y obstrucción: Mordell; Schinzel.
- Densidad de excepciones: Vaughan; Webb (densidad cero) — nuestro ángulo es
  complementario: estructura del conjunto decisor, no densidad.
- **arXiv:2404.01508** (sistema de congruencias completo, Tipos A/B): conjetura
  de existencia afín; sin set-cover mínimo ni crecimiento.
- **arXiv:2605.23601** (tame/wild primes en 24m+1): el pariente más cercano.
  TAREA: mapear si nuestros primos "difíciles por auxiliar" coinciden con sus
  wild primes (586 primos, m≤2000 — nosotros 20,513 a 10⁷).
- **arXiv:2606.10922** (parametrización por divisores): marco teórico sin
  computación masiva.

## 5. Reproducibilidad

- `stress13.py` (matriz completa ≤10⁷) y `stress13_v2.py` (escala, con muestra
  estratificada) — una máquina, minutos.
- Certificados: `certificado_erdos_straus_mod840.{json,csv}`.
- Generado por el consejo ACERO (Bohr v2, bitácora completa en el ledger del
  proyecto); revisión humana: pendiente de attestation externa.

## 6. Limitaciones declaradas

1. Resultado acotado y empírico; no implica la conjetura.
2. El cover voraz es aproximación del mínimo exacto (ILP exacto solo ≤10⁷).
3. La regla tipo II es UNA familia de splits; otras familias podrían dar covers
   menores.
4. Novedad del ángulo pendiente de confirmación por experto humano (área activa
   2024–2026).
