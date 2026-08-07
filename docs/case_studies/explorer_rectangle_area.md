# Caso en vivo — El Explorador reconstruye el área del rectángulo

Corrida real de `MathExplorer` (Codex CLI, sandbox sin red), sobre el objetivo que
Merari puso como ejemplo de la mentalidad exploratoria.

**Objetivo:** "encontrar la fórmula del área de un rectángulo de base b y altura h"

**Enfoques que el sistema inventó y corrió en paralelo (todos viables):**

| # | Enfoque (pieza de LEGO) | Candidato |
|---|---|---|
| 1 | Conteo por malla (contar celdas unitarias) | `A = b*h` |
| 2 | Derivación desde el cuadrado (escalar lados de A(s,s)=s²) | `A(b,h)=b*h` |
| 3 | Descomposición algebraica (aditividad + A(1,1)=1 → única forma bilineal) | `A(b,h)=b*h` |
| 4 | Casos límite y proporcionalidad (duplicar un lado duplica el área) | `A(b,h)=b*h` |

**Hipótesis sintetizada:** `A(b,h) = b·h` para `b,h ≥ 0` en las mismas unidades lineales.

**Veredicto:** `candidate` — `holds_empirically`, sin contraejemplo en **80 242 casos**.

**Por qué NO dice "verified":** los cuatro caminos convergen, pero el argumento es
una ecuación funcional bilineal, no una identidad que sympy pueda cerrar de un paso.
El sistema **se niega a llamarlo demostrado**: buscar mucho no es probar. Honestidad
heredada del `MathProbe`.

## Lo que este caso demuestra

No es que ACERO "no supiera" que el área es base×altura. Lo valioso es la **mentalidad**:
partiendo solo del objetivo, reconstruyó el resultado por **cuatro ángulos
independientes** y verificó que todos coinciden — sin que nadie le diera la fórmula.
Esa capacidad de *converger desde múltiples enfoques* es la que, apuntada a una
pregunta abierta, produce hipótesis genuinas en vez de una sola corazonada.

Reproducir:

```bash
python -m acero.cli.main portal   # o vía POST /api/math-explore
# { "goal": "encontrar la fórmula del área de un rectángulo de base b y altura h",
#   "approaches": 4, "rounds": 2 }
```
