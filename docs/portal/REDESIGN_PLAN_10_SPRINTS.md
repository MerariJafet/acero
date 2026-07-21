# Portal Redesign — Plan de 10 Sprints (estilo Proyecto CIO)

Requerimiento (2026-07-21, Merari): front tipo CIO Intelligence — chat persistente a
la izquierda + dashboard central; selector de investigaciones activas arriba;
"Nuevo proyecto"; dashboard de proyecto por FASES interactivas y minimizables con
barra de comentarios por sección; chat contextual según ubicación; Plan educativo
con temas toggleables; cursos LMS auto-vinculados a las investigaciones; sección
"Cursos" arriba.

Referencia analizada: `Proyecto CIO/dashboard/app.html` (+ style.css): `.topbar`
(marca + tenant-picker a la derecha + acciones), `.layout` flex, `.chat-panel`
384px (sugerencias, mensajes, form abajo), `.dashboard-panel` con secciones
colapsables y encabezado sticky.

## Sprints

| # | Alcance | Estado |
|---|---------|--------|
| S1 | Shell estilo CIO: topbar (marca, selector "Investigación Activa", Nuevo proyecto, Cursos, Sistema), chat izq, dashboard centro. Ids compatibles con tests (#nav, #view, login). | |
| S2 | Selector de proyectos + Nuevo proyecto (crea proyecto real) + dashboard general multi-investigación. | |
| S3 | `/api/projects/{id}/phases`: 6 fases (Hipótesis, Literatura, Teorías, Experimentos, Resultados, Conclusiones) desde artefactos reales; tarjetas gráficas minimizables. | |
| S4 | Click en fase → dashboard específico con items reales. | |
| S5 | Chat contextual (global/proyecto/fase/curso) + barra de comentarios por sección (pregunta scoped). | |
| S6 | Plan educativo: Codex genera índice de temas con toggles (apagar lo ya sabido); fallback determinista; persistido. | |
| S7 | Generar curso desde temas seleccionados → curso LMS persistido; estados Generar → Ir a curso → Completado. | |
| S8 | Visor LMS: lecciones siguiente/anterior, quiz con feedback, links, progreso; chat con contexto del curso. | |
| S9 | Sección "Cursos" (topbar) + sync: la investigación crece → el curso agrega temas (diff de ángulos no cubiertos). | |
| S10 | E2E actualizados al nuevo shell, tests de fases/plan/cursos, accesibilidad, evidencia, `make verify` verde. | |

## Principios que NO se negocian en el rediseño
- El copiloto es ayuda de razonamiento, NO evidencia; sin descubrimientos.
- Todo artefacto (plan, curso, fase) sale del estado REAL del proyecto con
  procedencia; los cursos citan la investigación que los origina.
- Fallbacks deterministas cuando Codex no esté disponible (sin IA fingida).
- Contexto del chat SIEMPRE visible (etiqueta de ubicación) y enviado al backend.
