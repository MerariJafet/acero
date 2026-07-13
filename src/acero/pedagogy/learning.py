"""Learning-artifact generator (Sprint 4 seed of the future Tutor).

The full Tutor comes later, but every pilot already produces human-learning
material so the investigator's understanding never falls behind the machine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_learning_docs(out_dir: str | Path, metrics: dict[str, Any],
                        skeptic: dict[str, Any]) -> dict[str, str]:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    best = metrics.get("best_model", "?")
    rec_k = metrics.get("recovered_k")
    true_k = metrics.get("true_k")

    files = {
        "intuition.md": """# Intuición

Un objeto caliente se enfría rápido al principio y luego cada vez más despacio,
acercándose a la temperatura del ambiente sin llegar a cruzarla. Esa forma
—caída rápida que se aplana— es una **exponencial**, no una recta ni un polinomio
arbitrario. Por eso el modelo `exponential_physical` gana: su *forma* coincide con
el fenómeno. Un polinomio de grado 9 puede imitar los datos de entrenamiento, pero
se dispara fuera del rango porque no tiene esa forma.
""",
        "mathematics.md": f"""# Matemáticas

Ley de enfriamiento de Newton:

    dT/dt = -k (T - T_env)   =>   T(t) = T_env + (T0 - T_env) e^(-k t)

- `T_env`: temperatura ambiente (asíntota).
- `T0`: temperatura inicial.
- `k`: tasa de enfriamiento (1/tiempo).

El ajuste recuperó **k ≈ {rec_k}** frente al valor real **k = {true_k}**.
Recuperar `k` es *estimación de parámetros de un modelo conocido*, no un
descubrimiento.
""",
        "code_walkthrough.md": """# Recorrido del código

1. Se generan datos sintéticos con ruido gaussiano a partir de la ley real.
2. La ecuación generadora se **oculta** al ajustador.
3. Cuatro modelos compiten: lineal, cúbico, exponencial físico, y polinomio 9.
4. Se dividen los datos en train/val/test (disjuntos) y un conjunto de
   **extrapolación** fuera del rango de entrenamiento.
5. Se mide RMSE en cada partición y contra un baseline ingenuo (media).
6. El exponencial se ajusta con búsqueda en `k` + mínimos cuadrados lineales.
""",
        "assumptions.md": """# Supuestos

- El ruido es aproximadamente gaussiano e independiente.
- `T_env` es constante durante el experimento.
- El muestreo temporal es representativo.
- "Mejor RMSE fuera de muestra" se usa como proxy de "mejor modelo" — es una
  heurística, no una verdad.
""",
        "human_questions.md": """# Preguntas para el investigador (responde ANTES de ver los resultados)

1. ¿Qué modelo esperas que generalice mejor fuera del rango y por qué?
2. ¿Por qué un polinomio de grado alto puede ganar en train y perder en
   extrapolación?
3. ¿Qué observación te haría *dudar* de la forma exponencial?
4. ¿Recuperar `k` cuenta como conocimiento nuevo? ¿Por qué no?
""",
        "knowledge_check.md": f"""# Verificación de comprensión

- [ ] Puedo explicar por qué `{best}` generaliza mejor.
- [ ] Puedo derivar T(t) desde dT/dt = -k(T - T_env).
- [ ] Puedo nombrar dos objeciones del escéptico y cómo se comprobaron.
- [ ] Entiendo por qué esto **no** es un descubrimiento científico.

Objeciones del escéptico registradas: {skeptic.get('n_objections', 0)}
(checks fallidos: {skeptic.get('n_failed_checks', 0)}).
""",
    }
    written = {}
    for name, content in files.items():
        p = d / name
        p.write_text(content, encoding="utf-8")
        written[name] = str(p)
    return written
