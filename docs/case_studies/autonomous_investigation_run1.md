# Caso — Primera investigación AUTÓNOMA (ACERO como investigador)

El sistema se planteó **sus propias** conjeturas (no se las dimos), las filtró por novedad
(OpenAlex) y las atacó con `MathProbe` + guardas. Todo sin red en el sandbox.

## Lo que se planteó solo (8 conjeturas precisas)

Áreas elegidas por el propio sistema: dominación en grafos, matchings inducidos bipartitos,
patrones consecutivos en permutaciones, particiones enteras, permanentes de matrices 0-1,
palabras binarias circulares, combinatoria aditiva en Z/mZ, posets. Todas precisas,
falsables y atacables por enumeración en casos pequeños. Novedad de las 8: `uncertain`.

## Lo que logró (atacó 5)

| # | Área | Veredicto | Evidencia |
|---|------|-----------|-----------|
| 1 | Dominación en grafos sin triángulos | holds_empirically | 11 305 grafos, sin contraejemplo |
| 2 | Matching inducido bipartito | holds_empirically | 44 567 casos |
| 3 | Ascensos en permutaciones que evitan 321 | holds_empirically | 4 118 888 casos |
| 4 | Paridad de partes impares en particiones | **refuted** | contraejemplo **n=1** |
| 5 | Permanente de matrices 3-regulares 0-1 | holds_empirically | 49 919 casos |

## Lectura honesta

**Comportamiento de investigador, sí:** planteó preguntas propias, precisas y diversas;
las probó exhaustivamente; **refutó una con contraejemplo concreto**; conservó 4
supervivientes. Ese ciclo generar→probar→refutar/conservar es investigación real.

**Pero sin Eureka (y es honesto):**
- La refutación (#4) es un **caso borde trivial** (n=1): la conjetura estaba mal planteada
  en el borde, no es un hallazgo profundo. Un investigador humano diría "falla trivial en
  n=1; ¿y si excluyo el borde y pruebo el núcleo?". El sistema **no hace esa segunda
  jugada**: reporta `refuted` y se detiene.
- Los 4 supervivientes quedan en `holds_empirically` (no probados) y con novedad
  `uncertain` (no confirmada). Son candidatos interesantes, no contribuciones.

## El PUNTO para ponerlo a investigar (no asistir)

El valor está en los **supervivientes** + la **segunda jugada** que hoy falta:

1. **Refinar refutaciones triviales:** si el contraejemplo es un borde (n muy pequeño),
   excluirlo y re-atacar el núcleo sustantivo de la conjetura.
2. **Empujar supervivientes hacia PRUEBA:** en vez de más fuerza bruta, intentar
   demostración (inducción/formal) o entender *por qué* se cumple.
3. **Profundizar novedad + elevar a revisión humana** los que aguanten.

Ese bucle —refinar, probar, escalar— es lo que convierte generar-y-testear en
investigación. Es el siguiente build.

Datos: `scratchpad/investigation_results.jsonl`.
