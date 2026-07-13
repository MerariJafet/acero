# Matriz de Autonomía

Define qué puede hacer ACERO por sí mismo (`auto`), qué requiere aprobación
humana (`human_required`) y qué está prohibido (`forbidden`). La fuente de verdad
es [`policies/autonomy.yaml`](../../policies/autonomy.yaml); esta tabla la resume.

| Acción | Nivel | Racional |
|---|---|---|
| Leer archivos locales | auto | Reversible, sin riesgo. |
| Escribir en el workspace | auto | Confinado al workspace del proyecto. |
| Ejecutar pruebas locales | auto | Reversible. |
| Ejecutar código en sandbox | auto | Aislado; red off; límites de recursos. |
| Crear entidades científicas | auto | Con reglas de integridad + procedencia. |
| Recuperación léxica (BM25) | auto | Local, sin costo. |
| Obtener metadatos abiertos (arXiv/Crossref) | human_required | Red + límites de tasa. |
| `git commit` | human_required | Cambia el historial del repo. |
| `git push` | human_required | Efecto externo. |
| Git destructivo (reset --hard, borrar ramas) | forbidden | Irreversible. |
| Borrar resultados negativos | forbidden | Viola preservación de negativos. |
| Modificar secretos | forbidden | Riesgo de seguridad. |
| Activar LLM de pago | forbidden* | Costo; requiere habilitación explícita de política. |
| Crear recursos en la nube | forbidden | Costo. |
| Publicación automática | forbidden | Requiere revisión humana. |
| Crear cuentas externas | forbidden | Efecto externo. |
| Enviar correos / contactar investigadores | forbidden | Efecto externo. |
| Descargas masivas | human_required | Tamaño + licencia. |
| Experimentación física | forbidden | Fuera de alcance v1. |
| Protocolos biológicos/químicos | forbidden | Seguridad. |
| Afirmar un descubrimiento científico | forbidden | Requiere revisión + antecedentes. |

\* `forbidden` en el sentido operativo de esta sesión: la interfaz existe pero
está bloqueada por `costs.yaml` (`external_paid_services: false`). Habilitarla es
una decisión humana que también sube límites de gasto y desactiva el circuit
breaker.

## Cómo se hace cumplir
- `PolicyGuard.require_autonomous(action)` — lanza `PolicyViolation` si la acción
  no es `auto`.
- `PolicyGuard.check_cost(...)` — circuit breaker para cualquier gasto.
- `PolicyGuard.check_publication(...)` — exige revisión humana.
- Pruebas: `tests/unit/test_config_policies.py`.
