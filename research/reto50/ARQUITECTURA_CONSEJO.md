# ACERO — Arquitectura del Consejo de Investigación
### Documento para revisión por experto externo · 10 agosto 2026

ACERO es un sistema local-first de investigación matemática autónoma. Su núcleo es
un **Consejo de 18 personajes-científicos**, cada uno un módulo de software real con
un oficio, que atacan conjeturas bajo una **constitución de honestidad** cuyo techo
es siempre la revisión humana. Nada se publica solo; el sistema jamás declara
resuelto un problema abierto.

---

## 1. El flujo maestro

```
   PREGUNTA del humano (chat del portal)
        │
        ▼
   PREMISA SELLADA  ← guardián (porqué / medio / definiciones exactas; inmutable)
        │
        ▼
   HIPÓTESIS (Hilbert registra el enunciado como candidato falsable)
        │
        ▼
   ┌────────────────── BOHR (director dinámico) ──────────────────┐
   │  bucle: DECIDIR jugada → EJECUTAR personaje → OBSERVAR       │
   │  resultado real → decidir la siguiente. Sin guion fijo.      │
   │  Presupuesto: 200 jugadas / 7 días de pared (no por diseño   │
   │  del pensamiento: son topes de seguridad, no metrónomo).     │
   └──────────────────────────────────────────────────────────────┘
        │  cada jugada escribe EVIDENCIA en el ledger (kind tipado,
        │  con parent_id → todo cuelga de la hipótesis)
        ▼
   INFORME de Bohr (bitácora jugada a jugada + disposición HONESTA)
        + SUGERENCIA automática de siguiente ronda
        │
        ▼
   HUMANO (Merari): valida, redirige, o sella nueva premisa
```

Principio rector: **el texto de un LLM nunca es evidencia**. Evidencia = ejecución
verificada en sandbox, prueba mecánica (sympy/Z3), o contraejemplo concreto.

---

## 2. Los 18 del Consejo

| # | Personaje | Oficio | Módulo real | Produce en el ledger |
|---|-----------|--------|-------------|----------------------|
| 1 | **Hilbert** | Plantea conjeturas precisas y falsables | question_engine | `candidate` (hipótesis) |
| 2 | **Euler** | Cataloga técnicas y métodos aplicables | method_catalog | apoyo a decisión |
| 3 | **Hipatia** | Novedad: ¿ya se hizo? (multi-fuente: arXiv, etc.) | novelty_check | `literature` |
| 4 | **Arquímedes** | Catálogo de datasets/recursos | data resolvers | capacidad |
| 5 | **Da Vinci** | Diseño de experimentos | experiment_factory | `experiment` |
| 6 | **Kepler** | Cosecha anomalías → hipótesis nuevas | anomalies | `candidate` derivados |
| 7 | **Tycho** | Memoria de scripts que funcionaron (caché) | script_cache | reuso |
| 8 | **Popper** | Busca CONTRAEJEMPLOS computacionales | math_probe (sandbox) | `experiment`, `negative` |
| 9 | **Euclides** | Prueba simbólica (identidades, desigualdades, sumas) | formal_verify (sympy) | `lemma` |
| 10 | **Gödel** | Prueba mecánica SMT (∀/∃ sobre enteros/booleanos) | proof_assistant (Z3, en proceso hijo con techo de días y latido) | `lemma` |
| 11 | **Aristóteles** | Crítica hostil (revisor adversarial interno) | critic | `critique` |
| 12 | **Feynman** | Actitud hacker: interpreta, refina bordes, reformula | research_loop (HumanAttitude) | `reformulation` |
| 13 | **Bohr** | DIRECTOR: decide jugada a jugada (ver §4) | bohr.py | `decision` |
| 14 | **Gauss** | Empaqueta dossier publicable (techo: humano) | dossier | `dossier` |
| 15 | **Ramanujan** | Chispas laterales "¿y si…?" en fronteras | spark.py | `spark` |
| 16 | **Turing** | Programa/instala/corre/repara experimentos (horas) | turing.py + toolbox | `build` |
| 17 | **Noether** | Referee de journal (teorema vs evidencia vs conjetura; novedad) — arbitraje INTERNO, nunca sustituye al experto humano | noether.py | `review` |
| 18 | **Mendeleev** | Descubre patrones en datos verificados (ver §6) | patterns.py | `pattern` |

---

## 3. Herramientas transversales

- **TOOLBOX (LEGO):** catálogo máquina-legible de piezas por nivel de evidencia
  (prueba-simbólica / prueba-mecánica / cálculo-experto / evidencia-numérica /
  literatura). Incluye `ensure()` (instala por pip/docker) y `run_sage()` (Sage
  enjaulado en contenedor sin red).
- **Sandbox:** todo código generado corre en subproceso aislado (timeout 1800s,
  4GB, sin red). El código de los agentes jamás corre en el proceso del portal.
- **Escalera SAT** (`sat_escalation`): directo → portafolio de semillas →
  cube-and-conquer, institucionalizada como pieza.
- **Proveedores LLM:** Codex CLI (principal), Claude CLI, Ollama, mock para tests.
  Esquemas JSON estrictos en toda llamada estructurada.
- **Ledger:** SQLite con filas tipadas (`kind`), actor, `parent_id` (genealogía),
  estados. El dashboard entero se deriva del ledger — si no está en el ledger, no
  pasó.
- **Regla del 90% de recursos:** los trabajos pesados corren con `nice`, workers
  acotados y un guard que los FORMA EN FILA (pausa/reintento) si el sistema pasa
  del 90% de RAM. (Origen: un cómputo v1 sin límites apagó la máquina.)

---

## 4. ¿Quién orquesta? Bohr — y NO tiene flujo establecido

Hay dos modos, y esta distinción es central:

**Modo clásico (legado):** guion fijo Hipatia → Popper → Feynman → Gödel →
Aristóteles → Gauss. Existe y funciona, pero es rígido.

**Modo Bohr v2 (el vigente):** NO hay pipeline. Bohr recibe: (1) su conocimiento
del Consejo (quién es cada uno + el catálogo de piezas), (2) la premisa sellada si
existe, (3) el HISTORIAL de jugadas con sus resultados REALES verificados, y (4) el
presupuesto restante. Con eso **decide la siguiente jugada él solo**, jugada a
jugada, vía una llamada LLM con esquema estricto. Puede repetir a un personaje con
otro ángulo, pedir segunda opinión, darle horas de cómputo a Turing, reformular el
enunciado (reiniciar) o cerrar honesto. Cada decisión queda en el ledger con su
porqué.

### Las instrucciones EXACTAS de Bohr (traducción fiel del system prompt)

> Eres Niels Bohr dirigiendo el Consejo de ACERO. Tu papel: el humano que controla
> el flujo. Miras el ESTADO real (historial de jugadas y sus resultados
> VERIFICADOS) y eliges la SIGUIENTE jugada del menú. Piensas en términos de: ¿qué
> sé ya? ¿qué me falta saber? ¿quién del Consejo me lo consigue más directo?
>
> Estilo de dirección:
> - Repite una jugada SOLO con argumentos distintos (otro ángulo, otro presupuesto).
> - Pide segunda opinión (Aristóteles) antes de creerte cualquier resultado positivo.
> - Si el camino directo está agotado o PROBADO imposible, no insistas: Ramanujan.
> - Una chispa prometedora merece cómputo de verdad: Turing con presupuesto generoso.
> - Un lema logrado no vale nada sin novedad: Hipatia lo dictamina ANTES de Gauss.
> - Reformular está permitido — abandona enunciados muertos sin nostalgia.
> - El tiempo NO es restricción; la deshonestidad SÍ. Cierra solo con disposición honesta.
>
> CONSTITUCIÓN (innegociable):
> - JAMÁS declares resuelto un problema abierto. La validación final es HUMANA.
> - Texto de LLM no es evidencia. Evidencia = ejecución verificada o prueba mecánica.
> - Si nada maduró, 'needs_human_review' es un cierre digno — inflar es el único fracaso.

### El menú de jugadas (cada una con "qué hace" y "cuándo usarla")

| Jugada | Hace | Cuándo |
|---|---|---|
| hipatia | busca en literatura si ya existe | antes de invertir; tras un lema |
| popper | ataque computacional buscando contraejemplos | enunciado nuevo o refinado |
| feynman | interpreta el último resultado, refina bordes, reformula | ataque terminó y no es obvio qué sigue |
| godel | intento de PRUEBA mecánica (sympy/Z3) | sobrevivió ataques y huele a demostrable |
| ramanujan | chispas laterales "¿y si…?" con el catálogo LEGO | FRONTERA: métodos directos agotados |
| turing | programa, instala piezas, corre, repara (minutos→horas que Bohr fija) | idea concreta que necesita cómputo serio |
| aristoteles | crítica hostil del estado actual | antes de creerse un resultado |
| kepler | cosecha anomalías → hipótesis nuevas | experimentos con discrepancias |
| mendeleev | busca ESTRUCTURA en datos verificados (representaciones, leyes) | hay tabla de observaciones ≥5 filas y la pregunta es "¿qué estructura hay?" |
| noether | arbitraje de referee (interno) | resultado maduro que aspira a nota |
| gauss | empaqueta dossier | resultado verificado + novedad dictaminada |
| reiniciar | adopta enunciado nuevo | el actual se agotó, la reformulación abre camino |
| cerrar | disposición HONESTA + resumen | logrado, agotado, o toca decisión humana |

### Salvaguardas mecánicas del bucle (código, no prompt)

- **Guard anti-bucle:** 3 repeticiones consecutivas con resultado idéntico
  bloquean la 4ª — Bohr debe cambiar de jugada.
- **Disposiciones cerradas:** solo puede cerrar con una disposición del conjunto
  honesto (verified / formally_supported / partial_progress / refuted / dropped /
  needs_human_review…). Una disposición inventada se degrada a needs_human_review.
- **Guardián de premisa (`on_restart`):** todo "reiniciar" y toda reformulación de
  Feynman se contrasta contra la premisa sellada; la deriva se marca en el ledger
  (`drift`) y la ALERTA se anexa al historial que Bohr lee en la siguiente decisión.
- **Latido:** decidir y demostrar pueden tardar horas; ambos laten al tablero para
  que "pensando" nunca sea indistinguible de "colgado".
- **Ejecutor roto ≠ ciclo muerto:** una jugada que lanza excepción se registra y
  el ciclo continúa.

---

## 5. El guardián de premisa (jerarquía)

Al abrir una investigación se sella: **PORQUÉ** (objetivo irrenunciable), **MEDIO**
(instrumental) y **DEFINICIONES operativas exactas**. El sello es inmutable
(resellar crea versión). Bohr lo lee antes que todo su conocimiento. Origen: en la
investigación de Erdős–Straus, la definición fuerte (criterio del divisor) se
degradó entre rondas a una condición trivial sin que nadie lo decidiera; una ronda
entera atacó la cerradura equivocada. Es el pre-registro (que ACERO ya usaba para
protocolos) aplicado a la pregunta misma. No bloquea: hace la deriva VISIBLE y la
convierte en decisión humana explícita.

---

## 6. Mendeleev — patrón ≠ descubrimiento

Pipeline: **FeatureLab** (representaciones derivadas controladas: log, razones,
módulos…, cada una con receta reproducible) → descubridor estadístico
(correlaciones, invariantes, estabilidad bootstrap) → descubridor simbólico
(gramática corta de leyes; manda el compromiso explicación/complejidad) →
**consenso pesado por INDEPENDENCIA**: `independent_views` cuenta representaciones
distintas de los datos, no métodos — dos métodos sobre la misma matriz son la misma
foto. Todo candidato lleva: causalidad NO ESTABLECIDA, rivales H1–H4 (X→Y, Y→X,
causa común, artefacto), contraejemplos, y procedencia completa (hash del dataset,
semilla, parámetros). Convertir un patrón en conjetura es trabajo del Consejo
(Popper/Gödel/gate), nunca de Mendeleev. Su ficha en el portal muestra un mapa de
grafos EN VIVO (patrones ↔ variables).

---

## 7. Límites conocidos (para el ojo del experto)

1. **El chequeo de deriva es por LLM**, no mecánico: el guardián puede fallar en
   sutilezas. Mitigación: guardián caído ≠ aprobación; el sello viaja completo.
2. **`cover_exact` es exacto respecto del llavero k ≤ 240** — una llave óptima
   mayor no se ve. El límite va declarado en cada fila del dataset.
3. **El arbitraje de Noether es interno**: nunca sustituye revisión externa real.
4. **Bohr es un LLM decidiendo**: sus jugadas son tan buenas como su contexto; las
   salvaguardas son mecánicas pero la estrategia no lo es.
5. **Los descubridores de Mendeleev son clásicos** (sin GNN) por diseño: entran
   solo si un benchmark demuestra valor añadido sobre lo clásico.
6. **holds_empirically jamás se auto-promueve** a verified; la promoción es humana.

---

## 8. Estado vivo (al corte de este documento)

- Investigación Erdős–Straus con premisa sellada v1 (llave dinámica k(p) como
  porqué; criterio del divisor como definición). Ronda 5 en curso.
- Dataset `cover_growth.json`: 13 hitos hasta 10⁹ (extendiéndose a 10¹²),
  1.59M primos duros con el criterio fuerte; cover greedy 6→18. Discrepancia
  documentada con la tabla externa (6 vs 5 en 10⁵, llavero acotado).
- Portafolio Caccetta–Häggkvist n=14: 5 semillas Z3 en paralelo (techos 168h/240h).
