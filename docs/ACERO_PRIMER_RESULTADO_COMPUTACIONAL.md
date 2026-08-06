# ACERO — Primer resultado computacional end-to-end (caso de estudio)

Primera corrida completa del pipeline proactivo, con honestidad epistémica.

## El flujo (todo automático salvo precisar la afirmación)
1. **Barrido masivo** (`sweep`): generó 10 conjeturas; **8 sobrevivieron** el filtro
   paralelo de novedad (anti-Erdősgate) + EVA; 2 descartadas (HARKing, trivial).
2. **Probador matemático** (`math_probe`): sobre una variante FUERTE y precisa de
   graceful labeling, el agente escribió código, enumeró árboles y **la refutó en el
   1er intento** con un contraejemplo concreto.
3. **Verificación independiente**: recomputé el contraejemplo con código propio
   (no el del agente) → **CONFIRMADO**.
4. **Paquete verificable**: empaquetado para que un tercero corra `python verify.py`
   (sin red, sin ACERO) → `INTACT` + hash para su attestation.

## El resultado (verificado)
**Afirmación (REFUTADA):** para todo árbol T (3≤n≤11) existe un etiquetado graceful
en el que algún **centro** de T recibe etiqueta en {0, n−1}.
**Contraejemplo (n=6):** aristas `(0,1),(0,2),(0,3),(1,4),(4,5)`, centro = vértice 1.
Tiene **12 etiquetados graceful**, pero en **ninguno** el centro recibe 0 o 5.
Ver `docs/case_studies/graceful_center_counterexample.py` (corre en <1s).

## Honestidad (lo que ESTO es y NO es)
- **Es**: una demostración de que el sistema completo produce un resultado
  **decidido y verificable de forma independiente**, con abstención honesta cuando no
  demuestra (la primera conjetura dio `holds_empirically`, NO "resuelto").
- **NO es**: la resolución de un problema abierto famoso. La afirmación refutada es una
  **variante fuerte de juguete** (la precisé yo); es un hecho matemático menor pero real.
  Para un resultado *publicable de peso* hay que apuntar a una afirmación **precisa Y
  novedosa** (que pase el checador de novedad) y que el probador decida.
- La lección del "Erdősgate" respetada: `holds_empirically` **nunca** se llama prueba;
  solo `verified` (formal) o un contraejemplo confirmado cuentan como decisión.

## Mejora pendiente detectada en vivo
Los reintentos 2–3 del probador crashearon (`rc=1`): el retry regenera desde cero. A
endurecer: que el retry parta del último código que corrió y solo cambie el método.
