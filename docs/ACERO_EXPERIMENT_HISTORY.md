# ACERO — Historia Experimental Forense (Fase 2 del prompt maestro)
### Reconstrucción de cómo HA investigado ACERO, no solo cómo está programado · 2026-08-10

> Fuentes primarias: `acero_data/acero.sqlite` (ledger, 67 proyectos) +
> `research/reto50/` + `docs/`. Regla: UNKNOWN donde no hay evidencia; los
> FRACASOS se documentan con el mismo detalle que los éxitos; la deriva de claims
> tras ver datos se señala explícitamente.

---

## 1. Censo del ledger: 67 proyectos

| Bloque | Proyectos | Fechas | Naturaleza |
|---|---|---|---|
| Pipeline clásico empírico | 8 (Posición Tierra, Epigenética, Fulton gap, Ruido cuántico, PubChem, Periodo femenino, Valle de radios + re-análisis) | 19-25 jul | Ciencia con datos externos |
| Sondas sueltas | 2 (Conjeturas, Lehmer totiente) | 6-7 ago | Exploración sin cierre |
| Piloto del Consejo | Decaimiento monótono de coherencia | 7-8 ago | Primer ciclo Consejo en física |
| **Reto 50** | 50 proyectos | 8 ago (~4h) | Barrido autónomo de 50 problemas abiertos |
| Post-Reto (mate dirigida) | Lema CH k=3; Chispa mod 840; Bohr humo; Aristóteles v2; Teorema llave 23 | 8-9 ago | Semilleros del programa Erdős–Straus |
| **Programa principal** | Erdős–Straus llave variable + cover — **VIVO** | 10 ago | 429 filas; premisa SELLADA |

---

## 2. El programa Erdős–Straus: ronda por ronda

**Precursores**: R50-06 probó el lema de escalamiento (novedad NULA declarada — ya
en la literatura). La chispa "cuadrados duros mod 840" logró cobertura de las 6
clases duras hasta 10⁵ pero Aristóteles devolvió `sin_revision` **dos veces** (bug
del crítico — corregido después). La NOTA_COVERING_SETS: 1,587,581 primos duros
≤10⁹ todos decididos por algún k≤255; k=23 cubre 71.994% intrínseco exacto a 10⁹.
**Noether (arbitraje interno): `revision_mayor`** con objeciones correctas y
demoledoras, todas incorporadas al texto final. Teorema de la llave 23: k=23 decide
todo p≡19 y p≡22 (mod 23) — teorema mecánico real; clases 5 y 14 excepcionales sin
explicación (pregunta abierta honesta).

### Ronda 1 (23 jugadas, ~2.3h) — `partial_progress`
Sin premisa sellada aún. Ramanujan generó 5 chispas. **El instrumento se
auto-refutó antes que la hipótesis**: Turing declaró PIPELINE_NO_SANO cuando un ILP
devolvió cover=0 "cubriendo" 10⁸ (Aristóteles lo cazó por incoherencia interna).
Feynman: "la señal fuerte no es el cover pequeño sino que k=23 cubra proporción
creciente". **El único holdout que funcionó como debe**: Aristóteles exigió
train/test, y esa prueba encontró **p=5003 (clase 803 nueva)** que refutó la
cobertura universal aprendida. Sin deriva; criterio fuerte del divisor intacto.

### Ronda 2 (23 jugadas, 1762.9s) — `partial_progress`
Gödel refutó la Hipótesis A acotada a la primera (**p=3889**). Turing declaró
BLOQUEADO_CERTIFICADO sobre la ley de crecimiento: "no hay definición operacional
local de cover(N); infinitas extensiones exactas reproducen los tres puntos" — los
puntos 5/8/10 eran **datos externos no reproducidos**, no objeto matemático.
**Noether rechazó dos veces**: "trazabilidad reproducible, no avance matemático".
Bohr se negó a llamar a Gauss: "insistir sería inflar trazabilidad finita como
teorema".

### Ronda 3 (23 jugadas, 1916.7s) — **AQUÍ NACE LA DERIVA**
La reconciliación con la tabla externa produjo DISCREPANCIA_SEMANTICA_DE_T (la
tabla no era interpretable bajo las definiciones internas). **Jugada 14 — la
deriva**: Feynman reformuló introduciendo `C(p,k)=1 ⟺ p+k≡0 mod 4` — **la condición
fuerte del divisor desapareció del enunciado**. La sugerencia de cierre lo admite
textualmente: *"La definición completa… quedó desplazada por una semántica reducida
C(p,k) ⇔ p+k≡0 mod 4; falta reconciliar."* Gödel tuvo conflicto formal-vs-búsqueda
y **ACERO se abstuvo** (conducta correcta). Lemma PROVED pero, como diría R4,
trivial.

### Ronda 4 (42 decisiones; **SIN report de cierre en el ledger**)
Trabajó todo bajo la semántica reducida. Aristóteles confirmó a la 2ª decisión:
"aritmética modular casi tautológica". Siguió una **máquina de picar conjeturas**:
Feynman propone, Popper refuta — **6 negatives CONFIRMED** con contraejemplos
mínimos exactos (K=1/[5], K=1/[3,5], K=2/[3,7], K=3/[5,13], K=12/[3,5], K=11/[3,7]).
El único positivo que sobrevivió fue el que tocaba MECANISMO (biyectividad CRT de
x→x^K). Veredicto del lado humano en PLAN_COVER_GROWTH.md: **"La Ronda 4 se perdió
exactamente aquí"** — clasificó una semántica que no era el problema.
Metodológicamente valiosa (la cadena refutación→reformulación funcionó 6 veces);
matemáticamente sobre Erdős-Straus, casi nada. Salida: **sellar una premisa**.

### Ronda 5 (EN VIVO; 38+ decisiones)
Premisa `prem_B7JTWQPT_1` SELLADA con la lección de R4 codificada. Mendeleev corrió
dos veces y **solo produjo correlaciones triviales** (r=1.000 entre variables
derivadas unas de otras) — Bohr lo dijo sin piedad: "Mendeleev solo encontró
correlaciones triviales". **Policía de desviaciones en vivo**: Turing usó
`C_surrogate` (bloqueado), `bound_k=300` cuando la premisa exige ≤240 (degradado),
y una "refutación" con puertas 169/209/221 **que no son primos** (invalidada por
Aristóteles). El guardián emitió **2 drift FLAGGED leves** — pero constató que el
criterio fuerte NO se sustituyó (la deriva grave de R3/R4 no se repitió). Estado:
tabla verificada p→K(p) con 4519 filas + certificados. La reconciliación 6-vs-5
sigue pendiente.

---

## 3. Investigaciones empíricas y el NO-GO

**Valle de radios (astro, el fracaso mejor documentado)**: rivales explícitas
H0-H5 incluido nulo. Resultado `RESULTADO_INCONCLUSO`: el placebo `sy_kepmag`
(0.050) **igualó la señal [Fe/H]** (0.047); el cross-match colapsó a 0.56%; la
verificación cruzada discrepó y ACERO **degradó su propio resultado**. Re-análisis:
el coeficiente se contrae 59% al controlar detectabilidad, CI cruza cero.
**Decisión final: NO-GO** — no se preregistró confirmatoria, no se tocó CKS/TESS,
el negativo se conservó. El claim cambió en la dirección correcta.

**Decaimiento de coherencia (física)**: Popper refutó tres versiones sucesivas con
contraejemplos estructurales (no bordes). Hipatia: "ya resuelta en la literatura".

**Reto 50**: 45 needs_human_review, 2 formally_supported (lemas clásicos, "novedad
NULA" declarada), 0 falsos positivos en 50 intentos imposibles.

**Caccetta–Häggkvist**: de timeout a 4s por FORMULACIÓN (no hardware). n≤13 proved,
n=14 unknown a 24h. Cube-and-conquer naive: solo 1.6% de cubos cerró. Las 5 semillas
murieron por el OOM del cover v1 (~40h perdidas; z3 no reanuda estado); relanzadas.
Hipatia dictaminó novedad **ASENTADA** (Hamidoune 1987, Hoàng-Reed 1987) — el
anti-Erdősgate funcionó en vivo.

---

## 4. Síntesis

### (a) ¿Conocimiento nuevo validado? Ninguno todavía — y el sistema lo dice en cada cierre.
El candidato real a contribución es el objeto cover/k=23, que sobrevive
precisamente porque su peor crítico interno (Noether) fue obedecido. El resto:
verificaciones de leyes conocidas o re-derivaciones clásicas, todas declaradas como
tales.

### (b) Fracasos y callejones (con la razón) — 16 documentados
Los más instructivos: ILP cover=0 (pipeline roto detectado por incoherencia),
SEÑAL_FUERTE de cobertura 100% out-of-sample (murió con p=5003 — era memorización de
clases vistas), **la semántica reducida C→mod 4 (el callejón más caro: una ronda
entera)**, cascada de 6 conjeturas parcheadas contraejemplo a contraejemplo (solo el
paso a mecanismo produjo algo verificado), Mendeleev ×2 sin filtro de trivialidad
(cero valor), CH n=14 sin checkpoint (OOM mató 5×40h), Cuboide sin timeout (colgó el
ciclo — fix posterior).

### (c) Estrategias con evidencia
**Repetir**: "no creer un positivo sin segunda opinión hostil" (la más rentable —
invocada como constitución en ≥8 jugadas, cazó todos los falsos positivos); exigir
train/test antes de creer cobertura; sanear el instrumento antes que la hipótesis;
contraejemplo mínimo→reformulación explícita; abstención ante conflicto formal (no
moneda al aire); arbitraje interno estilo referee; sellar premisa + guardián;
certificados con hashes + mutation testing.
**Evitar**: comparar contra números externos no reproducidos (bloqueó B durante 3
rondas y fabricó la crisis de R3); sustituir silenciosamente definiciones caras por
baratas (costó R4 — ya prohibido por premisa); parchear enunciados sin hipótesis de
mecanismo; pattern-mining sin filtro de trivialidad; SAT directo más allá del techo
medido; cómputos largos sin aislamiento de RAM ni checkpoint; confiar en un crítico
que falla en silencio.

### (d) ¿Los resultados de rondas anteriores INFLUYEN en las decisiones de hoy, o solo se archivan?
**Influyen, por cinco mecanismos verificables — con una excepción.**
1. **`suggestion` → claim siguiente (principal, literal)**: el claim de R3 es
   palabra por palabra el enunciado propuesto al cierre de R2; el de R4, el de R3.
2. **Contexto histórico embebido en el claim**: cada claim resume refutaciones
   previas (p=5003, p=3889, el conflicto Gödel).
3. **Premisa sellada como memoria dura**: codifica la lección de R4 y el guardián
   la inyecta en cada decisión, emitiendo drift.
4. **Vigilancia adversarial informada por historia**: Aristóteles calibra su
   escepticismo con los fracasos previos de la misma investigación.
5. **Herencia entre proyectos**: Reto-50 → revisión humana → chispa mod 840 → nota →
   llave 23 → programa de llave variable.

**La excepción (honestidad obligada)**: el EJE PRINCIPAL tiene memoria operativa
real (claim, premisa, guardián, crítico); la PERIFERIA se archiva y solo revive por
decisión humana — las chispas no elegidas, los patterns triviales, y los 45
supervivientes del Reto 50 no alimentaron ninguna ronda posterior salvo los 2
elegidos a mano. **Esto responde la pregunta clave del revisor: el PolicyEngine v1
NO aprende de los resultados pasados para elegir mejor el experimento siguiente —
la influencia histórica es por el claim/premisa/crítico, no por un modelo que
mida qué estrategias funcionaron.** Ese es exactamente el salto a Bohr híbrido v2.

---

### Nota del auditor
Lo que el ledger demuestra es un patrón raro y valioso: **las refutaciones están
mejor documentadas que los éxitos**, la deriva de definición fue detectada, nombrada
y bloqueada institucionalmente, y el único candidato real a contribución sobrevive
porque su peor crítico fue obedecido. El riesgo abierto más concreto: la
reconciliación 6-vs-5 del cover en 10⁵ sigue pendiente en la Ronda 5 viva — si se
resuelve documentando el porqué, la deriva de R3 queda cerrada de verdad; si se
maquilla, se repite el patrón que costó la Ronda 4.
