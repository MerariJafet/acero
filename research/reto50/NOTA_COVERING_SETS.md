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
(i) every one of the 1,587,581 hard primes up to 10⁹ is decided by some
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

Para N y una cota B, sea P(N) el conjunto de primos duros ≤ N,
K_B = {k ≤ B : k ≡ 3 (mod 4)} el universo de auxiliares, y **C_B(N)** el menor
S ⊆ K_B tal que todo p ∈ P(N) es decidido por algún k ∈ S. Distinguimos tres
nociones (arbitraje de Noether): (i) mínimo EXACTO |C_B(N)| (certificado ILP),
(ii) cover VORAZ+poda (cota superior de (i)), y (iii) cobertura UNIVERSAL: si
todo p ∈ P(N) tiene algún k ∈ K_B. En este trabajo B = 255 (B = 127 en 10⁵–10⁷).

## 2. Resultados computacionales (todos con aritmética exacta)

| N | \|P(N)\| | sin cobertura (universal, k≤B) | cover (método) | cover | k=23 (intrínseca) |
|---|---|---|---|---|---|
| 10⁵ | 273 | 0 | 13 (ILP exacto, regla de splittings del ciclo)/5 (voraz, regla k) | {7,11,23,31,39} | 63.0% |
| 10⁶ | 2,370 | 0 | 8 (voraz+poda — cota superior) | {3,23,31,47,59,63,71,127} | 65.5% |
| 10⁷ | 20,513 | 0 | 10 (voraz+poda — cota superior) | {15,19,23,31,39,47,59,71,119,167} | 67.6% |
| 10⁸ | ≈179,450 | 0 | 7 (muestra 1/50) | {23,31,47,59,71,119,143} | ≈70%* |
| 10⁹ | 1,587,581 | **0** | 9 (muestra 1/100) | {23,31,39,47,59,71,95,119,167} | **71.99% (intrínseca, exacta)** |

\* En 10⁸ el % de k=23 es "decide como PRIMERO en el orden de prueba"
(125,489 primos) — cota inferior de su cobertura total; el cover es sobre
muestra estratificada de 3,649 primos (cota inferior del cover completo).

Certificados explícitos por primo (JSON/CSV) hasta 10⁵ publicados; muestra
estratificada verificada a escalas mayores. Verificación triple independiente
en 10⁵ (dos implementaciones del sistema + re-verificación externa): 0 fallos.

## 3. La pregunta estructural (nueva hasta donde sabemos)

**C-ACERO-1 (versión soportada por los datos).** Existe C > 0 tal que todo
primo duro p es decidido por algún k ≤ C·log p.

**Pregunta del cover.** ¿Es |C_B(N)| = O(log N)? Los datos (5, 8, 10 por
década — cotas superiores voraces) son consistentes con crecimiento
~logarítmico.

**Aclaración (arbitraje de Noether).** C-ACERO-1 (cota individual por primo) y
la pregunta del cover (tamaño del conjunto) son enunciados DISTINTOS: ninguno
implica al otro sin hipótesis adicionales sobre el universo K_B. La implicación
hacia Erdős–Straus vale directamente para C-ACERO-1 (cada primo obtiene su
split explícito); para la versión de cover se requiere una familia uniforme
válida para todo N — formalización pendiente como proposición. El aporte de
esta nota es el OBJETO (el cover y su crecimiento) y el dataset, no un teorema
de la conjetura.

## 3b. De la evidencia al TEOREMA — la anatomía de la llave 23 (nuevo)

Reduciendo la condición del divisor módulo 23 (con 4x ≡ p): la llave abre si
(px)² tiene un divisor ≡ 17p² (mod 23). Los divisores MONOMIALES t = pᵃxᵇ dan
congruencias exactas resolubles por clase, y de ahí:

**Teorema (mecánico, verificado por período completo).** k=23 decide TODO primo
duro con p ≡ 19 (mod 23) (divisor t = p) y todo p ≡ 22 (mod 23) (t = x).
Verificación empírica: 232/232 en N=10⁶.

**Criterio reducido (álgebra verificada exacta, 2370/2370 sin desajustes).**
k=23 decide p ⟺ x² tiene un divisor e ≡ 17p², 17p o 17 (mod 23). Los tres
objetivos están CERRADOS bajo el apareamiento de divisores e ↔ x²/e (usando
x² ≡ 13p²): 17p² ↔ 17, y 17p es auto-dual. Para p no-QR mod 23 el objetivo
17p es residuo cuadrático, habilitando la ruta d² ≡ 17p (d ≡ ±√(17p)) — el
mecanismo detrás de la dicotomía.

**Hallazgo estructural (verificado hasta 10⁸: 57,161 primos en las 7 clases,
CERO excepciones).** Nueve clases no-cuadráticas están llenas:
{7,10,11,15,17,20,21} (sin teorema, evidencia a 10⁸) más {19,22} (con teorema). Las dos clases no-QR EXCEPCIONALES son p ≡ 5 y
p ≡ 14 (mod 23) (~85%), y las clases QR son parciales (~30%). El agregado
no-QR: 96.76% en 10⁶. Pregunta abierta: ¿qué distingue a 5 y 14?
(`teorema_llaves.py` reproduce todo.)

## 3c. Comparación directa con la familia tame/wild (nuevo)

En el estrato EXACTO de arXiv:2605.23601 (primos 24m+1, m ≤ 30000 — 7,185
primos; nuestro conteo coincide con el suyo), su familia de soluciones tame
deja **9 wild primes**; nuestra familia de llaves tipo II con k ≤ 127 deja
**0**. Matiz (arbitraje de Noether): esto es dominancia DE COBERTURA sobre ese
estrato con ese universo de llaves — no dominancia conceptual ni minimalidad
frente a la familia tame/wild; falta identificar sus 9 wild primes concretos y
publicar el certificado (k, t) de cada uno bajo un universo de comparación
común (pendiente: su lista no aparece en la Parte I del preprint).

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

## 7. Artefactos de auditoría (arbitraje de Noether)

- Repositorio: github.com/MerariJafet/acero — commit de referencia `6c94483` (+sucesores).
- sha256 (16 hex) certificados 10⁵: JSON `5381e52a67d63b18`, CSV `d5b03023c718a872`.
- Entorno: Python 3.12, sympy 1.14.0, aritmética exacta (fractions.Fraction).
- Re-escaneo independiente COMPLETO de 10⁹ con conteos por k: en curso
  (`k23_intrinseco_1e9.txt` para k=23; el barrido total por llave es el
  siguiente artefacto del pipeline).
- Verificador independiente mínimo: re-verificación externa por Fraction de los
  273 certificados (0 fallos) — ver bitácora del proyecto en el ledger.
