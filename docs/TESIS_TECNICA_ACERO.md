# ACERO — Tesis técnica del sistema
### Un sistema operativo de investigación científica autónoma, local-first, con honestidad constitucional
**Merari Acero · 10 de agosto de 2026 · ~52,000 líneas de código fuente, ~16,400 de tests, 180 commits**

---

## 1. Tesis

**ACERO es una máquina para explorar espacios de conocimiento enormes sin mentirse a
sí misma.** La apuesta central no es "un LLM que hace ciencia" — es una
*arquitectura* donde múltiples agentes con oficios distintos producen, atacan y
clasifican evidencia bajo reglas mecánicas que ninguno puede saltarse, con el
humano como validador final e insustituible.

Tres decisiones fundacionales lo definen:

1. **El texto de un LLM nunca es evidencia.** Evidencia = ejecución verificada en
   sandbox, prueba mecánica (sympy/Z3), o contraejemplo concreto. Un párrafo
   convincente vale cero.
2. **La honestidad es estructural, no aspiracional.** No depende de que un prompt
   diga "sé honesto": hay compuertas (gate), disposiciones cerradas, registros
   inmutables y verificadores independientes que hacen que inflar un resultado sea
   *mecánicamente difícil*.
3. **El techo es humano.** El estado máximo que ACERO puede otorgar solo es
   "listo para revisión humana". Jamás declara resuelto un problema abierto;
   jamás publica solo.

---

## 2. Anatomía general

```
┌─────────────────────────────────────────────────────────────────┐
│  PORTAL (FastAPI + front vanilla, 127.0.0.1:8611/portal)        │
│  3 MODOS: Investigación · Aprender · Económico                  │
├─────────────────────────────────────────────────────────────────┤
│  CONSEJO (18 personajes = 18 módulos)  ←  BOHR dirige           │
├─────────────────────────────────────────────────────────────────┤
│  MAQUINARIA EPISTÉMICA                                          │
│  gate constitucional · EVA · rivales · pre-registro · holdout   │
│  linaje de evidencia · grafo de independencia · nulos · CAUSA   │
├─────────────────────────────────────────────────────────────────┤
│  MOTORES DE CIENCIA                                             │
│  math_probe · formal_verify (sympy) · proof_assistant (Z3)      │
│  frontier_toolkit · sat_escalation · patterns · spark · turing  │
├─────────────────────────────────────────────────────────────────┤
│  INFRAESTRUCTURA                                                │
│  ledger (SQLite, genealogía) · sandbox (subproceso/docker)      │
│  TOOLBOX (catálogo LEGO) · providers LLM · knowledge_mesh       │
│  regla del 90% (RAM/VRAM) · selfeval/release gates              │
└─────────────────────────────────────────────────────────────────┘
```

**Todo pasa por el ledger.** Cada acción de cada personaje escribe una fila tipada
(`kind`) con actor, `parent_id` (genealogía hacia la hipótesis) y estado. El
dashboard entero se deriva del ledger: si no está en el ledger, no ocurrió. Esto
hace al sistema auditable por construcción — anti-HARKing estructural.

---

## 3. Los tres modos

| Modo | Qué es | Motor |
|---|---|---|
| **Investigación** | El corazón: conjeturas → Consejo → evidencia → informe. Portada = el Consejo; cada personaje abre su tablero real. | `investigator_bridge` + `bohr` |
| **Aprender** | Tutor de 3 paneles (árbol de conceptos anidado + chat + lienzo KaTeX/Mermaid) que lleva de un tema general hasta la FRONTERA del conocimiento y desde ahí siembra investigaciones reales. | `pedagogy/learning` |
| **Económico** | Asesor de 3 paneles sobre las finanzas reales de NEXUS (conector `integrations/nexus.py`): ideas de crecimiento + loop de crítica adversarial. | `portal/economics` |

Los tres comparten el mismo shell (chat izquierda + dashboard centro) y el mismo
ledger.

---

## 4. El Consejo: 18 oficios

### Fase creativa / planteamiento
- **Hilbert** — convierte temas en conjeturas PRECISAS y falsables (`candidate`).
- **Euler** — catálogo de métodos: qué técnica matemática aplica a qué problema.
- **Arquímedes** — catálogo de datasets y recursos computables.
- **Da Vinci** — diseña experimentos (fábrica: fetch confiable → codegen
  consciente del esquema → sandbox → reparación).
- **Ramanujan** — chispas laterales "¿y si…?" cuando hay FRONTERA declarada; lee
  el TOOLBOX y propone ideas con probabilidad, analogía y experimento barato
  (`spark`).
- **Mendeleev** — descubre patrones en datos verificados (§7) (`pattern`).

### Fase de investigación / registro
- **Hipatia** — novedad multi-fuente: ¿ya se hizo? (arXiv/OpenAlex/Crossref vía
  knowledge_mesh) con juez clasificador (`literature`).
- **Tycho** — memoria de scripts que funcionaron (caché de Popper) — reintentos
  gratis.
- **Kepler** — cosecha anomalías de resultados → hipótesis nuevas.
- **Bohr** — el director (§5) (`decision`).

### Fase crítica / prueba
- **Popper** — ataque computacional masivo buscando contraejemplos (sandbox,
  aritmética exacta) (`experiment`, `negative`).
- **Euclides** — prueba SIMBÓLICA: identidades, desigualdades, sumas/productos
  telescópicos, límites (sympy con timeout duro en proceso hijo) (`lemma`).
- **Gödel** — prueba MECÁNICA SMT: ∀/∃ sobre enteros/reales/booleanos (Z3 en
  proceso hijo, techo de días, latido cada minuto) (`lemma`).
- **Turing** — el hacker-matemático: escribe el experimento en Python, instala
  piezas que falten (pip/docker/Sage), lo corre, lee el error, repara y reintenta
  durante horas (`build`).
- **Aristóteles** — crítica hostil: reconstruye la afirmación exacta, busca
  alternativas no descartadas y qué la falsaría (`critique`).
- **Noether** — referee de journal: clasifica sin piedad teorema / evidencia /
  conjetura, ataca la novedad, exige chequeos faltantes. Arbitraje INTERNO — nunca
  sustituye al experto humano (`review`).

### Publicación
- **Gauss** — empaqueta el dossier con evidencia y límites explícitos; estado
  máximo: `needs_human_review` (`dossier`).
- **Feynman** — la actitud hacker entre fases: interpreta el último resultado,
  refina bordes, reformula, propone la segunda jugada (`reformulation`).

---

## 5. Bohr: cómo decide (la pregunta central)

**No hay pipeline.** Existe un modo clásico legado (guion fijo), pero el vigente es
**Bohr v2**: un bucle *decidir → ejecutar → observar* donde cada jugada se elige
mirando los resultados REALES de las anteriores.

**Entradas de cada decisión:** (1) conocimiento del Consejo — quién es cada uno +
catálogo TOOLBOX (incluye datos operativos como "PARI 7× para factorización
masiva"); (2) la **premisa sellada** si existe — leída ANTES que todo; (3) el
historial de jugadas con veredictos verificados; (4) presupuesto restante (200
jugadas / 7 días — topes de seguridad, no metrónomo).

**Su system prompt (fiel):** "Miras el ESTADO real y eliges la SIGUIENTE jugada del
menú. Piensas: ¿qué sé ya? ¿qué me falta saber? ¿quién del Consejo me lo consigue
más directo?" — con reglas de estilo: repetir jugada solo con argumentos distintos;
segunda opinión (Aristóteles) antes de creer un positivo; frontera agotada →
Ramanujan; chispa prometedora → Turing con horas; lema sin novedad no vale →
Hipatia antes de Gauss; reformular sin nostalgia; "el tiempo NO es restricción, la
deshonestidad SÍ".

**Menú de 13 jugadas** (cada una con "qué hace / cuándo"): hipatia, popper,
feynman, godel, ramanujan, turing, aristoteles, kepler, mendeleev, noether, gauss,
reiniciar, cerrar. La respuesta viene en JSON de esquema estricto (acción + razón +
expectativa + parámetros específicos como presupuesto de Turing o dataset de
Mendeleev) — la razón queda en la bitácora.

**Salvaguardas mecánicas (código, no prompt):**
- Anti-bucle: 3 resultados idénticos consecutivos bloquean la 4ª repetición.
- Disposiciones de cierre cerradas (verified / formally_supported /
  partial_progress / refuted / dropped / needs_human_review); inventar una la
  degrada a needs_human_review.
- **Guardián de premisa**: todo `reiniciar` y toda reformulación se contrasta
  contra el sello; la deriva se registra (`drift`) y la alerta se inyecta al
  historial que Bohr lee. Guardián caído ≠ aprobación.
- Latido: decidir (LLM) y demostrar (Z3) pueden tardar horas — ambos laten al
  tablero; "pensando" nunca es indistinguible de "colgado".
- Ejecutor roto ≠ ciclo muerto; jugada fallida se registra y se sigue.
- Al cerrar: informe-bitácora + **sugerencia automática de siguiente ronda**
  (hilos no explorados, pista pendiente, claim listo para lanzar).

---

## 6. La maquinaria epistémica (la constitución)

Esta capa existe porque los LLM se engañan con facilidad. Cada pieza nació de un
modo de fallo observado:

| Pieza | Contra qué defiende |
|---|---|
| **Epistemic gate** (motor + reglas por tipo: hipótesis, experimento, inferencia, publicación…) | promociones de estado sin evidencia suficiente |
| **Pre-registro sellado + régimen A/B** (CCC-1) | ajustar el protocolo después de ver resultados |
| **Guardián de premisa** | deriva silenciosa de la PREGUNTA misma entre rondas |
| **Search Space Ledger** | "encontré X" ocultando cuánto se buscó (deuda de exploración) |
| **Holdout manager** | contaminación confirmatoria (datos de confirmación inaccesibles hasta el final) |
| **Linaje de evidencia + grafo de independencia** | contar como "independientes" evidencias que comparten origen — independencia CALCULADA, no declarada |
| **Catálogo de nulos por estructura** | señales que también aparecen en datos aleatorizados |
| **CAUSA** (capa causal) + validación sustantiva de aristas | correlación vestida de causalidad |
| **EVA** (analista de vulnerabilidades epistémicas) + ClaimReconstructor | atacar una versión débil o distinta de la afirmación real |
| **Teorías rivales** (generador) + panel adversarial plural | enamorarse de la primera explicación |
| **Genealogía anti-HARKing** (ledger semántico) | reescribir la hipótesis para que "siempre fue" lo encontrado |
| **Taxonomía de novedad + ContributionScore** | vender lo ya conocido como nuevo (anti-Erdősgate) |
| **Selfeval + baseline sellado** | regresión de capacidad silenciosa (capacidad ≠ rendimiento de reloj) |
| **Reliability**: red team, mutation testing, calibración, scorecard | sobreconfianza sistemática |
| **Publicación**: attestation externa + paquete de verificación exportable | "confía en mí" — terceros pueden verificar sin ACERO |

---

## 7. Mendeleev y el descubrimiento de patrones

El añadido más reciente (hoy). Pipeline: **FeatureLab** (representaciones derivadas
controladas: log, razones, módulos — cada una con receta reproducible) →
descubridor estadístico (correlaciones, invariantes, estabilidad bootstrap) →
descubridor simbólico (gramática corta de leyes; gana el compromiso
explicación/complejidad) → **consenso pesado por INDEPENDENCIA** (representaciones
distintas de los datos, no número de métodos).

Contrato `PatternCandidate`: causalidad NO ESTABLECIDA siempre, rivales H1–H4
(X→Y, Y→X, causa común, artefacto), contraejemplos, procedencia completa (hash,
semilla, parámetros). **Patrón ≠ descubrimiento**: convertirlo en conjetura es
trabajo del Consejo. Su ficha muestra un mapa de grafos EN VIVO. GNN/autoencoders
quedan condicionados a que un benchmark demuestre valor sobre lo clásico (y a la
GPU, §9).

---

## 8. Ciencias que puede investigar

- **Matemáticas** (la más profunda hoy): teoría de números (Erdős–Straus:
  paridad clásica lograda + descubrimiento de covering-sets verificado a 10⁹),
  combinatoria/grafos (Caccetta–Häggkvist acotado: n≤13 PROBADO por Z3, n=14 en
  ataque), lógica/conteo (Z3), álgebra/análisis simbólico (sympy), geometría
  aritmética vía Sage enjaulado.
- **Astronomía** (plugin + lab): series de tiempo, inferencia sobre catálogos
  reales (caso vivo: valle de radios/metalicidad — cerró honesto en NO-GO).
- **Física** (plugin): identificación de dinámicas (SINDy-style), librería de
  términos, simetrías, derivaciones de primeros principios.
- **Química y Genética** (plugins con lab básico).
- **Dominio económico** (NEXUS, modo Económico).
- **Meta-ciencia**: benchmarks de sí mismo (recovery bench, integrity benchmark,
  gauntlets de caos/red-team/revisión externa).

La arquitectura de dominios es de **plugins con contratos** (`domains/core`):
añadir una ciencia = implementar su lab + reglas de gate, no tocar el núcleo.

---

## 9. Recursos: la regla del 90%

Nacida de un incidente real (hoy): un cómputo sin límites agotó la RAM y apagó la
PC. Ahora es ley del sistema:

- **RAM**: trabajos pesados con `nice`, workers acotados, y guard que los forma en
  FILA (pausa/reintento) si el sistema pasa del 90%.
- **VRAM** (GPU RTX ~8GB, driver pendiente de activar): `gpu.py` con `status()`
  honesto, `wait_for_vram()` al 90%, y **protocolo de aviso previo** — ningún
  trabajo CUDA arranca sin confirmación humana (requiere reinicio para drivers).
- **Criterio GPU**: tensores SÍ (embeddings, GNN, bootstraps masivos); lógica
  irregular NO (Z3, factorización, DP) — un solver no es un tensor.
- **Eficiencia medida, no supuesta**: PARI 7× sympy en factorización
  (benchmark verificado, registrado en el TOOLBOX donde Bohr y Turing lo leen).

---

## 10. Estado actual (10-ago-2026)

**Investigación Erdős–Straus (llave dinámica)** — la prioridad estratégica:
- Premisa SELLADA v1: porqué = fórmula k(p) adaptativa con razón explicada;
  medio = ley de crecimiento de cover(N); definición = criterio fuerte del divisor.
- Dataset `cover_growth.json`: 15+ hitos, 7.3M primos duros procesados (rumbo a
  10¹¹ por etapas con revisión humana entre décadas); cover greedy 6→18 con
  tres hitos consecutivos en 18 — forma compatible con crecimiento logarítmico,
  pendiente de que Mendeleev lo dictamine con rivales.
- Reconciliación honesta abierta: nuestro cover_exact(10⁵)=6 vs 5 externo
  (llavero acotado k≤240, documentado).
- Ronda 5 EN VIVO con el guardián activo. Rondas 1–4: partial_progress honestos;
  la 4 fue cerrada por humano al detectar deriva de premisa — el incidente que
  motivó al guardián.

**Caccetta–Häggkvist n=14**: 5 semillas Z3 en paralelo (168h/240h de techo).

**Backlog estratégico**: publicación con attestation externa (pendiente de
decisión humana sobre la NOTA); Hipatia→Obsidian con embeddings (plan LIT-1..4,
primer uso real de la GPU); fase neuronal de Mendeleev condicionada a benchmark.

**Calidad**: suite unitaria en verde; matriz de aceptación 23/23; 5 supervisores/
crons autónomos con reglas de honestidad embebidas.

---

## 11. Lo que ACERO no hace (límites declarados)

1. No valida externamente: Noether es interna; la validación real es de expertos
   humanos (attestation existe pero requiere terceros).
2. No garantiza estrategia óptima: Bohr es un LLM bien instrumentado — sus
   salvaguardas son mecánicas, su criterio no.
3. El chequeo de deriva de premisa es por LLM (con el sello completo a la vista),
   no una verificación formal.
4. `cover_exact` es exacto respecto del llavero declarado, no absoluto.
5. Sin GPU activa aún; la fase de tensores está preparada pero no estrenada.
6. Los problemas ABIERTOS siguen abiertos: ACERO produce evidencia, lemas
   acotados y candidatos — el día que algo parezca más, el protocolo es
   frenar, verificar, arbitrar y llamar al humano. Por diseño.
