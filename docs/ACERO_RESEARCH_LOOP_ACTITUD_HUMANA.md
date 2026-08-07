# ACERO — ResearchLoop + Actitud Humana (de asistente a investigador)

> "Un humano diría 'falla trivial en n=1; ¿y si excluyo el borde y pruebo el núcleo?'.
> Necesito un pequeño filtro que se llame ACTITUD HUMANA, con esa chispa creativa —
> observar como humano o con actitud de hacker (no para hackear, sino para descubrir
> opciones que aún no se ven)— e incluirlo en el loop." — Merari

## El salto

Antes: **generar → probar → refutar/conservar**, y parar. Eso es *testear*.
Ahora, el `ResearchLoop` añade la **segunda jugada** de un investigador:

```
conjetura
  → PROBAR            (MathProbe + guardas anti-refutación-falsa)
  → ACTITUD HUMANA    (la chispa: ¿trivial? ¿otra forma? ¿fortalecer? ¿probar?)
  → ACTUAR            (refinar y reatacar / intentar prueba / escalar a humano)
  → persistir (ledger) + disponer
```

## El filtro `HumanAttitude` (la chispa creativa)

Un paso con **persona deliberada**: un matemático astuto con **mentalidad de hacker —
para DESCUBRIR, no para romper**. Recibe la conjetura y qué pasó al atacarla, y **ve lo
que la máquina no ve**:

- si la refutación es un **borde trivial** (n=1, caso degenerado) → lo dice y da un
  `refined_statement` que **excluye el borde y conserva el núcleo**;
- si algo **sobrevivió** → propone jugada de investigador: intentar **demostración**
  (¿inducción? ¿biyección? ¿invariante?), una versión **más fuerte y fértil**, o un
  **ángulo no probado**;
- siempre devuelve `alternative_angles` — las opciones creativas aún no vistas.

Es reutilizable: se le puede dar **siempre** esta actitud a cualquier resultado.
`next_action ∈ {refine_and_retry, strengthen_and_retry, attempt_proof,
escalate_to_human, drop}`.

**Honestidad:** la actitud humana genera IDEAS y mejores enunciados; los **veredictos**
siguen saliendo del probador y sus guardas. La chispa nunca "declara" un resultado.

## Disposiciones

`verified` (prueba formal directa del enunciado completo) · **`formally_supported`**
(un LEMA núcleo del argumento está probado por sympy; la reducción al enunciado completo
queda para confirmación humana) · `refuted` (contraejemplo real) · `needs_human_review`
(sobrevivió / requiere demostración humana, con boceto) · `dropped`.

## Cerrar el ciclo (formalizar el boceto)

Cuando la actitud humana reduce el problema a un hecho verificable, el loop no solo
escala: **FORMALIZA** ese núcleo. `_attempt_proof` → (1) intenta prueba formal directa
del enunciado completo vía el Explorador; si no, (2) pide al FORMALIZADOR un lema núcleo
como `formal_claim` y lo verifica con `formal_verify`. Si sympy lo **prueba** →
`formally_supported` (con el lema y la prueba adjuntos). Honestidad estricta: probar el
lema **no** prueba por máquina el puente de reducción, así que **nunca** se declara
`verified` completo por esta vía — eso queda reservado a una prueba formal directa.

## Un detalle que el propio loop reveló

En el primer intento, la actitud humana observó sobre la refutación de la conjetura de
particiones: *"n=1 es de borde, pero revela algo más fuerte: la regla por n mod 4 está
probablemente orientada al revés o incompleta"* y pidió `refine_and_retry`. El loop la
ignoró porque exigía la bandera `trivial=true`. Se corrigió: **se honra la jugada creativa
siempre que proponga un enunciado más filoso**, no solo en el caso estrictamente trivial.
Justo el tipo de segunda jugada que queríamos.

## API

`POST /api/research-loop` `{ "statement": "...", "max_depth": 3 }` → `{disposition,
final_statement, final_verdict, sketch, trail:[{depth, verdict, trivial, observation,
alternative_angles, next_action}...]}`.

## Archivos

- `src/acero/science/research_loop.py` — `HumanAttitude` + `ResearchLoop`.
- `src/acero/portal/app.py` — endpoint `/api/research-loop`.
- `tests/unit/test_research_loop.py` — 6 tests offline (todo inyectable).
