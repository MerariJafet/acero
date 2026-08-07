# ACERO — El Consejo como flujo ÚNICO (fusión, no duplicación)

Objetivo (Merari): que **el flujo SEA los 14 personajes**. Todo lo que ya existe
(hipótesis, literatura, experimentos, misiones, loop autónomo, EVA, publicación) NO se
reescribe ni se duplica: se **re-hospeda bajo su personaje**. El Consejo es la puerta de
entrada; al hacer clic en un personaje se abre **su dashboard real** (sus fichas y procesos).

## Principio

- **No crear nada nuevo que ya exista.** Cada botón/panel actual se conserva; solo cambia
  DÓNDE vive: dentro de su personaje.
- **El Consejo (14 personas) es la primera pantalla** del proyecto.
- **Clic en personaje → su panel existente** (las fichas que le tocan).

## Mapa de fusión (cada personaje ← flujo/panel/endpoint que YA existe)

| Personaje | Al hacer clic muestra (panel EXISTENTE) | Endpoints/flows que absorbe |
|-----------|------------------------------------------|------------------------------|
| 🏛️ **Hilbert** | Fichas de **hipótesis** + generar preguntas (EVA) | `ws_hypotheses`, "Generar preguntas científicas (EVA)", fase *Hipótesis* |
| ♾️ **Euler** | Resultados del **barrido masivo** | `/api/projects/{id}/sweep` (⚡ Proactividad → Barrido) |
| 🔎 **Hipatia** | **Literatura** + chequeo de novedad | `/api/novelty-check`, fase *Literatura* (📚) |
| ⚙️ **Arquímedes** | **Catálogo** de piezas LEGO | `method_catalog` (nuevo panel liviano) |
| 🎨 **Da Vinci** | **Explorador**: enfoques que corrió | `/api/math-explore` (🧭 Explorador) |
| 🪐 **Kepler** | **Teorías/Conocimiento** (hipótesis sintetizada) | síntesis del explorador, fase *Teorías* |
| 🔭 **Tycho** | **Cerebro — Obsidian** (índice/memoria) | world model / `explorer_ledger`, "Sincronizar" |
| ❌ **Popper** | Fichas de **experimentos** + prober | `/api/math-probe`, fase *Experimentos* (⚗️) |
| 📐 **Euclides** | **Verificación formal** (sympy) | `/api/formal-verify` |
| 🔭 **Gödel** | **Prueba lógica/conteo** (Z3) | `proof_assistant` (dentro de confrontar) |
| ⚖️ **Aristóteles** | **EVA / objeciones / revisor** | EVA vulnerabilidades, panel adversarial, loop del Revisor |
| 🧩 **Feynman** | **Segunda jugada** (actitud humana) | `HumanAttitude` en `/api/research-loop` |
| 🎩 **Bohr** | **Director**: Misión completa + Loop autónomo (PI) | "Misión completa", Loop autónomo (Iniciar/Pausar/Tick) |
| 🏅 **Gauss** | **Publicación** + Resultados/Conclusiones | panel de publicación, fases *Resultados*/*Conclusiones* |

**Botones que hoy confunden → dónde quedan:**
- *"Misión completa"* y *Loop autónomo (Investigador Principal)* → dentro de **🎩 Bohr**
  (es el director; correr TODO el ciclo es su trabajo).
- *"Generar preguntas científicas (EVA)"* → **⚖️ Aristóteles** (crítica) o **🏛️ Hilbert**
  (plantear) según sea "encontrar vulnerabilidades" o "plantear preguntas".
- *⚡ Proactividad (Barrido/Novedad/Formal/Explorador)* → se reparte a **Euler/Hipatia/
  Euclides/Da Vinci** respectivamente.
- Las **6 fases** (Hipótesis…Conclusiones) siguen existiendo pero como el "avance" que ya
  alimenta las pelotas del Consejo; se llega a su detalle desde el personaje dueño.

## La conexión que CIERRA el círculo (fix #1)

Hoy el investigador matemático (Explorer/Probe/Gödel/ResearchLoop) corre **al lado** del
dashboard. La fusión exige que **escriba al ledger del proyecto**: al atacar un claim se
crea hipótesis → experimento → veredicto en el proyecto, y entonces las **fichas del
personaje**, los **KPIs** y las **pelotas del Consejo** se actualizan solos. Un puente
`investigator → ledger` (una función `record_to_project(pid, persona, result)`).

## Los 5 puntos a mejorar (con el #4 reencuadrado)

1. **Conectar investigador → ledger → dashboard** (arriba). *La #1.*
2. **Un solo disparador desde el Consejo**: clic en 🎩 Bohr → "Investigar este problema"
   corre el ciclo completo y las pelotas se mueven entre fases en vivo.
3. **Dedup de proyectos** por título/tema al crear.
4. **AMBICIÓN (reencuadrado): sí intentar resolver / aportar.** Para un problema abierto,
   el ResearchLoop no se detiene en `holds_empirically`: engancha a **Feynman** para
   reformular (probar una cota, una propiedad estructural obligatoria del contraejemplo,
   una variante más fuerte/débil), a **Gödel** para intentar un lema, y a **Popper** para
   empujar cotas de búsqueda. La honestidad se mantiene (no declarar prueba sin prueba),
   pero **la meta es aportar conocimiento nuevo**, no obedecer "es famoso, imposible".
5. **Endurecer el codegen** del prober (menos intentos que se caen).

## Cómo se implementa (incremental, sin romper nada)

1. `council.js`: el cajón del personaje deja de ser solo texto → **monta el panel real**
   de ese personaje (reusa las funciones de render que ya existen en `dashboard.js`).
2. Puente `investigator_bridge.py`: `record_to_project()` — escribe hipótesis/experimento/
   veredicto al ledger. Popper/Da Vinci/Gödel lo llaman al terminar.
3. Bohr: botón "Investigar" que orquesta el ciclo y escribe al ledger (las pelotas se mueven).
4. Retirar/re-hospedar los botones sueltos (no borrarlos: moverlos al personaje dueño).
5. Dedup + endurecer codegen.

> Nada se elimina; todo se re-hospeda. El resultado: **una sola narrativa — los 14
> personajes — que engloba todo el trabajo de investigación.**
