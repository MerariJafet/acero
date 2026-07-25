# ACERO — Manual de usuario y guía de la metodología

*Para cualquier persona. Aprende a usar el sistema y, sobre todo, a entender **por qué**
hace lo que hace. Léelo como un mini-curso: primero la idea, luego el flujo, luego el
"cómo" botón por botón, y al final las mejores prácticas.*

---

## Parte 1 — La idea en 2 minutos (¿qué es y por qué?)

ACERO es un asistente que hace **el trabajo pesado y reproducible de investigar con
datos públicos**, pero con una regla de oro:

> **La inteligencia artificial NUNCA es evidencia.** El modelo propone, razona y redacta;
> la evidencia sale de **código que corre sobre datos reales identificables**. Y **nada es
> un descubrimiento** hasta que un humano experto lo revisa y otro laboratorio lo replica.

¿Por qué tanta insistencia? Porque un sistema automático, si lo dejas suelto, se vuelve
una **máquina de producir positivos**: prueba mil variantes hasta que "algo sale
significativo", aunque sea casualidad, confusión o fuga de datos. ACERO está diseñado para
**impedirse a sí mismo ese autoengaño**. Esa disciplina es su mayor valor.

**El techo del sistema es "candidato a preprint".** Publicar, declarar un hallazgo o
aprobar algo lo hace **una persona**, nunca el programa.

---

## Parte 2 — La metodología (el corazón, explicado con manzanas)

ACERO piensa la ciencia como una cadena. Cada eslabón tiene un porqué:

1. **Comprender antes de criticar.** Reconstruye qué afirma una idea (población, variable,
   evidencia, supuestos) *antes* de atacarla. Criticar una caricatura no sirve.
2. **Buscar dónde podría fallar (EVA).** No para contradecir por contradecir, sino para
   encontrar la **ignorancia fértil**: ¿de qué supuesto depende? ¿hay confusión? ¿se
   probó en otra población? Cada debilidad se convierte en una **pregunta investigable**.
3. **Formular rivales.** Nunca una sola hipótesis favorita: la principal + la nula + al
   menos dos explicaciones alternativas. La ciencia avanza distinguiendo entre rivales.
4. **Diseñar una prueba que los distinga.** El equivalente científico de un "exploit": una
   observación que dé resultados **distintos** según cuál teoría sea cierta. Se prioriza
   por **cuánta información** aporta (en bits), no por lo llamativa que suene.
5. **Explorar libre, confirmar bloqueado.** Dos regímenes separados:
   - *Descubrimiento*: explora todo lo que quieras; el resultado es un **candidato**.
   - *Confirmación*: **congela el plan** (hipótesis, variable, prueba, regla de decisión) y
     su huella (hash) **antes** de abrir datos nuevos que el sistema no ha visto (*holdout*).
   Sin esta separación, "ver los datos y luego decidir" invalida la estadística.
6. **Ejecutar con controles.** Cada experimento corre en una caja aislada (sin internet),
   con **prueba nula** obligatoria y un **discriminador** explícito. Un "supports" exige una
   **segunda implementación independiente**.
7. **Preservar los negativos.** Un resultado negativo bien hecho **vale** y no se borra.
8. **Acotar la afirmación.** Un compilador de afirmaciones traduce la evidencia a la frase
   máxima permitida: *"asociado con"* (observacional), *"predice en esta población"*,
   *"efecto bajo estos supuestos"* (diseño causal válido), *"replicado"* (fuente
   independiente). Y **lintea** las sobreafirmaciones: si escribes "demuestra" o "causa" sin
   respaldo, te lo marca.
9. **Contar todo lo que exploraste.** Un "ledger" registra cuántas hipótesis, columnas,
   modelos y semillas probaste (la *deuda de exploración*), para no fingir que el análisis
   final fue el único.
10. **Independencia calculada, no declarada.** Dos datasets que comparten la misma raíz de
    curación **no** son independientes, aunque parezcan distintos. Un *holdout* del mismo
    dataset **jamás** cuenta como replicación.
11. **Panel de 8 críticos con mandatos incompatibles** (estadístico, causalista, detective
    de datos, revisor de novedad, etc.). Preservan el desacuerdo; si uno "duro" bloquea, se
    detiene el avance.

Si entiendes estos 11 puntos, entiendes ACERO. Todo lo demás son botones.

---

## Parte 3 — El flujo recomendado (paso a paso)

```
   ＋ Nuevo proyecto            →  escribe tu TEMA/PREGUNTA libre (el prompt)
        ↓
   🧠 Generar hipótesis         →  el sistema propone hipótesis guiadas por tu pregunta
        ↓
   ✓ Aprobar las buenas         →  tú decides cuáles valen la pena
        ↓
   🚀 Misión completa           →  por cada hipótesis aprobada corre TODO el ciclo
        ↓                            (literatura → experimentos → síntesis → rigor)
   🧭 Preguntas (EVA)           →  convierte las debilidades en preguntas fértiles
        ↓
   📜 Revisar dossiers           →  el techo: TÚ (revisión humana)
```

**El mejor flujo, en una frase:** escribe una **pregunta buena** → genera hipótesis →
aprueba pocas y buenas → lanza **una** Misión completa → deja que el rigor y el panel la
machaquen → revisa el dossier con calma.

---

## Parte 4 — El dashboard, componente por componente

Al entrar a una investigación ves, de arriba a abajo:

- **🧠 Cerebro — Obsidian.** Es el **almacenamiento e índice** del programa. Guarda TODO
  automáticamente (hipótesis, literatura, experimentos, dossiers) tras cada acción. No es
  opcional: es la memoria. El botón "↻ Sincronizar ahora" solo fuerza un guardado inmediato.
- **Mapa del proceso (stepper).** Las 6 fases en fila con su estado: ✓ con trabajo · ▶ aquí
  vas · • pendiente. Clic en cualquiera abre su tablero.
- **▶ Arranca la investigación.** Un botón grande **🚀 Misión completa** (el ciclo entero) +
  un acordeón **"⚙️ Pasos individuales (avanzado)"** para correr solo una parte.
- **🧭 Generar preguntas (EVA).** Encuentra vulnerabilidades → preguntas priorizadas +
  prueba discriminante.
- **KPIs globales** (papers, experimentos, hipótesis, dossiers).
- **Fichas de fase (mini-reportes).** Cada fase muestra sus **KPIs** (p.ej. experimentos:
  total / datos reales / apoyan / refutan / inconclusos), de qué **se nutre** y a qué
  **alimenta**, lo más reciente, y un **➜ Próximo paso**.

Dentro de **Hipótesis**, cada tarjeta trae su **mini-pipeline** propio
(💡 Propuesta → ✅ Aprobada → 📚 Literatura → ⚗️ Experimentos → 📜 Dossier) y botones:
**✓ Aprobar**, **🚀 Lanzar misión** (solo esa hipótesis), **🧭 Detalle**, **🎯 novedad**,
**🗑 Borrar** (con cascada y respaldo en el vault).

---

## Parte 5 — ¿Qué botón hace qué? (y qué absorbe la misión)

| Botón | Qué hace | ¿Necesario? |
|---|---|---|
| 🚀 **Misión completa** | ciclo autónomo por hipótesis aprobada | **el principal** |
| 🧠 Generar hipótesis | propone hipótesis del tema | sí, al inicio (la misión NO lo hace) |
| 📚 Investigar literatura | papers reales con DOI + retracción | **embebido en la misión** |
| ⚗️ Correr experimentos | propone + ejecuta con datos reales | **embebido en la misión** |
| 🎯 Evaluar novedad | asentada → frontera | opcional (prioridad) |
| 🔥 Cazar anomalías | discrepancias → hipótesis nuevas | opcional (nuevas ideas) |
| 🛰️ Vigilar literatura | escanea papers nuevos | opcional (mantenimiento) |
| 🌌 Investigación a fondo | mapa profundo del tema | opcional (exploración) |
| 🧭 Preguntas (EVA) | vulnerabilidades → preguntas + prueba | complementa el ciclo |

La **Misión completa absorbe** literatura + experimentos + síntesis + rigor. Los demás son
entradas (hipótesis, anomalías) o mantenimiento. **No corras todo a mano**: la misión es el
camino.

---

## Parte 6 — Sugerencias para usarlo bien

1. **Escribe una pregunta afilada**, no un tema vago. "¿El valle de radios depende de la
   metalicidad de forma que distinga fotoevaporación de pérdida por el núcleo?" es 10×
   mejor que "exoplanetas". El tema **siembra** las hipótesis.
2. **Aprueba pocas hipótesis buenas**, no todas. Menos y mejor.
3. **Lanza UNA misión completa** y deja que corra; no aprietes todos los botones.
4. **Usa EVA** para saber qué pregunta vale más la pena antes de gastar experimentos.
5. **Lee los negativos y los inconclusos** con el mismo respeto que los positivos — ahí
   está la honestidad.
6. **No confundas "confirmado en holdout" con "replicado".** Para replicar de verdad
   necesitas una **segunda fuente independiente**.
7. **El dossier es un borrador para ti**, no un paper. El techo eres tú.
8. **Chatea con el copiloto** (panel izquierdo) para preguntar sobre cualquier fase; su
   respuesta es ayuda de razonamiento, no evidencia.

---

## Parte 7 — Qué NO esperar (honestidad)

- ACERO **no descubre solo**. Encuentra estructura, la somete a crítica dura, y te entrega
  un candidato honesto y reproducible. Cruzar el umbral al "descubrimiento" es humano.
- La **ablación 100%→0% de falsos positivos** es evidencia interna preliminar (9 casos), no
  una validación externa definitiva.
- Necesita **datos independientes y armonizables** para una afirmación fuerte: el cuello no
  es descargar datos, es encontrar una **fuente de otra raíz** y compararla bien.

---

*Una línea para recordar:* **ACERO te ayuda a investigar sin engañarte a ti mismo — y se
detiene, a propósito, justo antes de la palabra "descubrimiento".**
