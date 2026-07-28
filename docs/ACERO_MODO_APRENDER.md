# ACERO — Modo Aprender (Learning)

El modo de entrada que cierra el ciclo **aprender → descubrir**: un tutor te lleva
de un tema general hasta la **frontera del conocimiento**, y cuando rozas una
pregunta sin respuesta la conviertes en una investigación real de ACERO.

## Entrada

Al iniciar sesión aparece un **selector de modo**: 🎓 **Aprender** o 🔬
**Investigación**. (También en la topbar: botón "🎓 Aprender"; el logo ACERO
vuelve al selector.)

## Dashboard de 3 paneles

```
┌─ 🧭 Tu recorrido ─┐┌──────── 🎓 Chat del tutor ────────┐┌─ 🎨 Lienzo ─┐
│ árbol ANIDADO de  ││ explicación leveled a tu profundidad││ fórmulas    │
│ conceptos:        ││ + subtemas para ramificar ↴         ││ (KaTeX)     │
│  átomo            ││                                     ││ diagrama    │
│   └ electrón      ││ [🛰️ alerta de frontera + 🚀 crear   ││ (Mermaid)   │
│      └ espín      ││  investigación cuando aplica]       ││ términos    │
│ (clic = navegar)  ││ caja de preguntar / profundizar     ││ conexiones  │
└───────────────────┘└─────────────────────────────────────┘└─────────────┘
```

- **Izquierda — árbol de tu recorrido.** Cada concepto es un nodo. Profundizar en
  un subtema crea un **hijo**; volver a una pregunta más global = clic en un
  **ancestro**. Ves el hilo exacto de cómo fuiste ahondando.
- **Centro — chat del tutor** (Codex→Claude). Explica el punto actual, adapta la
  profundidad a la ruta recorrida, y ofrece **subtemas** para ramificar. Puedes
  preguntar libremente dentro del nodo.
- **Derecha — lienzo.** Fórmulas en LaTeX (KaTeX), un diagrama Mermaid si ayuda,
  términos clave y conexiones con otras teorías. (KaTeX/Mermaid por CDN; sin red
  degradan a texto plano.)

## Frontera → investigación (cierre del ciclo)

Cada turno el tutor evalúa **honestamente** si la pregunta actual roza un problema
abierto sin respuesta asentada (`frontier.near` + `open_question`). Si sí, el chat
muestra una **alerta** y el botón **🚀 Crear investigación**, que siembra un
proyecto nuevo con esa pregunta como tema → entra al flujo completo de ACERO
(hipótesis → literatura → experimentos agénticos → loop del PI). La bandera de
frontera es una heurística de arranque; la novedad real la valida el pipeline.

## Endpoints / archivos

- `src/acero/portal/learning.py` — `LearningEngine` (start/ask/drill/get),
  `LearningTutor` (turno estructurado + evaluación de frontera). Sesión en
  `acero_data/learning/<sid>/{tree.json,messages.jsonl}`.
- API: `POST /api/learning/start`, `/{sid}/ask`, `/{sid}/drill`,
  `GET /{sid}`, `POST /{sid}/promote` (crea el proyecto).
- Front: `static/js/learning.js` (3 paneles), selector en `app.js`,
  KaTeX/Mermaid en `index.html`, estilos en `style.css`.
- `tests/unit/test_learning.py` — offline (tutor inyectado).

Regla epistémica: la prosa del tutor es **guía, nunca evidencia**; ningún hallazgo
se promueve a descubrimiento sin el pipeline + revisión humana.

## Reanudar + Perfil del aprendiz

- Al entrar a Aprender ves **tus lecciones guardadas** (tema · conceptos · fecha) para **reanudar** cualquiera otro día (persisten en `acero_data/learning/<sid>/`).
- ACERO mantiene un **perfil del aprendiz** (`acero_data/learning/profile.json`): en cada turno el tutor infiere tu **nivel** e **intereses** (`learner_signal`, en la misma llamada, sin costo extra) y se acumulan con tus temas y preguntas. Ese perfil se **inyecta en el prompt** de cada lección para calibrar profundidad, conectar con lo que te interesa y guiarte hacia lo que aún no dominas. Endpoint: `GET /api/learning` (sesiones + perfil).
