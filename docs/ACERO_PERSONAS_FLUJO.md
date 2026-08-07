# ACERO — Personajes y flujos (personalización por rol)

Cada flujo del investigador lleva el nombre de un personaje que se caracterizaba por ESE
trabajo. Así, para mejorar algo, vas **directo al personaje** (= su módulo real) y su
tarea. Este documento es la fuente de verdad: personaje → módulo → qué hace → a quién le
pasa → cuándo regresa y por qué → estado.

## El reparto (13 personajes)

| Personaje | Rol | Módulo real | Estado |
|-----------|-----|-------------|:--:|
| 🏛️ **Hilbert** | Plantea problemas/conjeturas precisas | `science/…` question engine + generador de conjeturas | 🟡 |
| ♾️ **Euler** | Genera en masa y en paralelo, filtra | `portal/sweep.py` (`SweepEngine`) | 🟡 |
| 🔎 **Hipatia** | Bibliotecaria: ¿ya se hizo esto? (novedad) | `discovery/novelty_check.py` (`NoveltyChecker`) | 🟢 |
| ⚙️ **Arquímedes** | Caja de herramientas/piezas LEGO | `science/method_catalog.py` (`MethodCatalog`) | 🔵 |
| 🎨 **Da Vinci** | Explora múltiples enfoques creativos, corre scripts | `science/math_explorer.py` (`MathExplorer`) | 🟢 |
| 🪐 **Kepler** | Sintetiza la hipótesis/ley desde los resultados | `MathExplorer._synthesize` | 🟡 |
| 🔭 **Tycho Brahe** | Registra y recuerda qué funcionó | `science/explorer_ledger.py` (`ExplorerLedger`) | 🔵 |
| ❌ **Popper** | Refuta: busca contraejemplos (falsación) | `science/math_probe.py` (`MathProbe`) | 🟡 |
| 📐 **Euclides** | Prueba formal simbólica (sympy) | `science/formal_verify.py` (`verify`) | 🟢 |
| 🧩 **Feynman** | Actitud humana/hacker: ve lo que otros no ven, refina, reduce | `science/research_loop.py` (`HumanAttitude`) | 🔵 |
| ⚖️ **Aristóteles** | Crítico: corrobora, exige evidencia, frena falsedades | guardas anti-refutación (`math_probe`) + EVA / panel adversarial | 🟢 |
| 🎩 **Bohr** | Director del bucle: decide refinar/probar/escalar | `science/research_loop.py` (`ResearchLoop`) | 🔵 |
| 🏅 **Gauss** | Editor riguroso: solo publica lo maduro (*pauca sed matura*) | `publication/external_validation.py`, `verification_packet.py`, `reliability/scorecard.py` | 🟡 |

Escala de estado: 🟢 sólido · 🟡 mejorable (punto débil identificado) · 🔵 nuevo
(prometedor, poco rodaje) · 🔴 débil (necesita trabajo).

## El flujo (quién le da la tarea a quién)

```
                       ┌─────────────────────────────────────────────┐
   OBJETIVO ──►🎨 Da Vinci ──(usa)──►⚙️ Arquímedes (piezas)          │
                   │  corre enfoques en paralelo (sandbox SIN red)    │
                   ▼                                                   │
              🪐 Kepler (sintetiza hipótesis) ──►🔭 Tycho (registra)  │
                   │                                                   │
   CONJETURA ─────►│                                                  │
   🏛️ Hilbert ──►🔎 Hipatia (¿novedosa?) ──►🎩 Bohr (director) ◄─────┘
                                                  │
                                                  ▼
                              ❌ Popper (ataca) ◄──(reintenta)── 🧩 Feynman
                                   │   │                              ▲
                        (cross-check)│   └─►⚖️ Aristóteles (corrobora)│
                                   ▼        │ si refutación NO         │
                              📐 Euclides    │ corroborada → regresa   │
                              (prueba formal)└─► a Popper / degrada     │
                                   │                                   │
                                   ▼                                   │
                              🎩 Bohr ──► 🧩 Feynman (segunda jugada) ─┘
                                   │        · trivial → refina y REGRESA a Popper
                                   │        · sobrevive → intenta prueba (Euclides)
                                   ▼        · si no reduce → escala
                              🏅 Gauss (publicación / validación externa / revisión humana)
```

## Detalle por personaje: entrada → trabajo → salida / regreso

- 🏛️ **Hilbert** — *entrada:* un área o nada. *trabajo:* plantea conjeturas precisas y
  falsables. *pasa a:* 🔎 Hipatia (novedad) → 🎩 Bohr.
- ♾️ **Euler** — *entrada:* un foco. *trabajo:* genera N hipótesis en paralelo y filtra
  por novedad+EVA. *pasa a:* 🎩 Bohr las supervivientes.
- 🔎 **Hipatia** — *entrada:* una afirmación. *trabajo:* busca en literatura (OpenAlex).
  *pasa a:* 🎩 Bohr con veredicto novedad. *regresa/frena:* si ya está resuelta, se
  descarta antes de gastar cómputo.
- ⚙️ **Arquímedes** — *entrada:* un objetivo. *trabajo:* ofrece las piezas LEGO
  relevantes (retrieval determinista). *sirve a:* 🎨 Da Vinci. *aprende:* `learn()`.
- 🎨 **Da Vinci** — *entrada:* un objetivo. *trabajo:* diverge en enfoques, corre cada
  uno como script. *pasa a:* 🪐 Kepler (los viables).
- 🪐 **Kepler** — *entrada:* enfoques viables. *trabajo:* destila UNA hipótesis + su
  forma formal. *pasa a:* ❌ Popper (confrontar) y 🔭 Tycho (registrar).
- 🔭 **Tycho** — *entrada:* resultados. *trabajo:* los persiste y **reofrece** como
  pistas en futuras corridas.
- ❌ **Popper** — *entrada:* una afirmación/hipótesis. *trabajo:* caza contraejemplos +
  cruza con 📐 Euclides. *pasa a:* 🎩 Bohr el veredicto. *vigilado por:* ⚖️ Aristóteles.
- 📐 **Euclides** — *entrada:* un claim formal. *trabajo:* prueba/refuta simbólicamente.
  *pasa a:* ❌ Popper / 🎩 Bohr.
- ⚖️ **Aristóteles** — *entrada:* una refutación. *trabajo:* exige corroboración; si es
  near-miss numérico, conflicto formal-vs-empírico, o contradice 2+ enfoques → **regresa
  a Popper** o degrada a candidato. *por qué:* nunca declarar falso lo verdadero.
- 🧩 **Feynman** — *entrada:* el resultado del ataque. *trabajo:* observa como hacker,
  ve estructura, refina bordes triviales, reduce a un lema. *pasa a:* ❌ Popper (reataca
  el núcleo) o 📐 Euclides (formaliza el lema) o 🏅 Gauss (escala con boceto).
- 🎩 **Bohr** — *entrada:* conjetura. *trabajo:* orquesta el bucle probar→Feynman→actuar.
  *decide:* `verified` / `formally_supported` / `refuted` / `needs_human_review`.
- 🏅 **Gauss** — *entrada:* un resultado maduro. *trabajo:* empaqueta, exige validación
  externa humana, marca listo-para-revisión. *techo:* revisión científica humana.

## Evaluación de estado (quién puede mejorar su trabajo)

| Personaje | Estado | Punto a mejorar |
|-----------|:--:|-----------------|
| 🎨 Da Vinci | 🟢 | Sólido: 10/10 respuestas correctas en el benchmark. |
| 📐 Euclides | 🟢 | Sólido: ahora prueba identidades, sumatorias y productos. |
| ⚖️ Aristóteles | 🟢 | Sólido (nuevo): eliminó las 3 refutaciones falsas decisivas. |
| 🎩 Bohr | 🔵 | Nuevo: lógica de control simple; ampliar decisiones. |
| 🧩 Feynman | 🔵 | Nuevo/prometedor: segundas jugadas reales; falta rodaje. |
| ⚙️ Arquímedes | 🔵 | 20 piezas; hacer que crezca solo (learn tras descubrir). |
| 🔭 Tycho | 🔵 | Guarda bien; explotar más la memoria (reuso de caminos). |
| 🏛️ Hilbert | 🟡 | Plantea preciso, pero a veces conjeturas con bordes triviales. |
| ♾️ Euler | 🟡 | Existe; poco rodaje reciente. |
| 🪐 Kepler | 🟡 | No codifica de forma FIABLE la forma formal (sumatorias) → se queda en empírico. |
| ❌ Popper | 🟡 | Aún genera refutaciones falsas (las atrapan las guardas); endurecer el codegen de contraejemplos. |
| 🏅 Gauss | 🟡 | Sin cerrar un ciclo real de attestation externa (pendiente). |
| 🔎 **Hipatia** | 🟢 | **De 🔴 a 🟢:** en vivo detectó 2 de 3 "supervivientes" como YA RESUELTOS con cita concreta (bipartito ← grafos de incidencia de planos proyectivos; 321-consecutivo ← "double descent" en un survey). Endurecida contra timeouts (reintento + timeout mayor). |

**Prioridad de mejora sugerida:** (1) ❌ Popper (falsas refutaciones), (2) 🪐 Kepler
(codificación formal), (3) 🏅 Gauss (cerrar publicación).

> Nota: los otros modos (Aprender, Económico) tendrán su propio reparto cuando toque —
> este documento cubre el **investigador**.
