# Caso — La "segunda jugada": ResearchLoop + Actitud Humana en vivo

Dos conjeturas reales de la investigación autónoma, atacadas ANTES (solo probador) y
DESPUÉS (con el loop de investigador + actitud humana).

## A — Conjetura de particiones (antes: refutación trivial)

**Antes (solo probador):** `refuted` con contraejemplo **n=1**. Superficial: no dice nada.

**Después (ResearchLoop):**
- **paso 1** (n≥1): refuted, actitud detecta borde trivial (n=1 solo tiene [1]) → refina a n≥2.
- **paso 2** (n≥2): refuted, otro borde puro (n=2 → [2], 0 partes impares) → refina a n≥3.
- **paso 3** (n≥3): refuted **no trivial**. La actitud observa el porqué:
  > *"el módulo 4 es la pista equivocada. Hay un invariante inmediato: en cualquier
  > partición de n, la paridad de la cantidad de partes impares coincide con la paridad
  > de n"* — y propone la identidad exacta que lo explica.

**Mejora:** de "falso en n=1" (ruido) → **refutación sustantiva + la razón estructural**
(por qué la regla mod-4 no tiene sentido). Disposición honesta: `refuted`.

## B — Permutaciones que evitan 321 consecutivo (antes: callejón sin salida)

**Antes:** `holds_empirically` (sin contraejemplo en 4.1M casos). Punto muerto.

**Después:** la actitud humana ve la **estructura oculta** y casi lo demuestra:
> *"evitar 321 consecutivo ⟺ no hay dos descensos adyacentes ⟺ la palabra de signos U/D
> no contiene DD. En una palabra binaria de longitud m=n−1 sin DD, los descensos están
> separados por ascensos, así que #D ≤ ⌈m/2⌉, y #ascensos = m−#D ≥ ⌊m/2⌋."*

Eso es **exactamente la cota conjeturada** (≥ ⌊(n−1)/2⌋). Disposición: `needs_human_review`
con el **boceto** listo para un humano. ACERO **no** dice "demostrado" (el boceto no está
mecánicamente verificado) — escala honestamente. Ese es el techo correcto.

**Mejora:** de "aguanta empíricamente" (muerto) → **reducción estructural + boceto de
prueba prácticamente completo**, entregable a un humano.

## Veredicto

El loop convierte *testear* en *investigar*: pela bordes triviales hasta el núcleo,
encuentra la razón estructural, y reduce/boceta pruebas — manteniendo la honestidad
(nunca declara lo que no verificó). Datos: `scratchpad/research_loop_demo.json`.
