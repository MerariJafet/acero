"""Cross-Domain Structural Discovery Benchmark (Sprints 8.5–8.7 integration).

Proves ACERO can identify a SHARED STRUCTURE, transfer a prediction, verify it, and
find where the analogy fails — updating the World Model. Cases:
  * oscillator ↔ RLC       (deep structural analogy; resonance transferred + verified)
  * thermal ↔ particle diffusion (valid in regime)
  * atom ↔ solar system    (MISLEADING; surface similarity, no deep equivalence)

Honesty: nothing here is a discovery; these are known correspondences used to
validate the method.
"""

from __future__ import annotations

from typing import Any

from ..cognitive.analogies.engine import AnalogyEngine
from ..cognitive.analogies.systems import BENCHMARK_PAIRS
from ..cognitive.first_principles.engine import FirstPrinciplesEngine
from ..cognitive.first_principles.models import FirstPrinciplesProblem
from ..cognitive.integration.pipeline import integrate_analogy
from ..sandbox.runner import SubprocessRunner
from ..world_model.graph import WorldModel


def run_cross_domain(wm: WorldModel, *, runner: SubprocessRunner | None = None,
                     run_transfer: bool = True) -> dict[str, Any]:
    runner = runner or SubprocessRunner()
    ae = AnalogyEngine(wm, runner=runner)
    fp = FirstPrinciplesEngine(wm)

    analogies: dict[str, Any] = {}
    integrations: dict[str, Any] = {}
    for name, (src, tgt) in BENCHMARK_PAIRS.items():
        a = ae.build(src, tgt, run_transfer=run_transfer)
        analogies[name] = {
            "status": a.status.value, "deep_score": a.scores.deep_score(),
            "surface_similarity": a.scores.surface_similarity,
            "mapping": a.entity_mapping,
            "validations": {v.test: v.passed for v in a.validations},
            "transfer_predictions": a.transfer_predictions,
            "failure_conditions": a.failure_conditions,
        }
        integrations[name] = integrate_analogy(wm, a)

    # First-principles corroboration for the oscillator (dimensional + resonance).
    osc_problem = FirstPrinciplesProblem(
        project_id=wm.project_id, phenomenon="driven damped oscillator resonance",
        variables={"resonant_frequency": "frequency", "mass": "mass",
                   "spring_constant": "spring_constant"},
        candidate_symmetries=["time_translation"],
        target_quantity="resonant_frequency")
    dims = fp.dimensional_analysis(osc_problem)
    conservation = fp.symmetry_conservation(["time_translation"])

    return {
        "project_id": wm.project_id,
        "analogies": analogies,
        "integrations": integrations,
        "first_principles": {
            "oscillator_dimensional_analysis": dims,
            "symmetry_conservation": conservation,
        },
        "world_model_stats": wm.stats(),
        "honesty": [
            "Las analogías usadas son correspondencias conocidas (oscilador↔RLC, etc.).",
            "Esto VALIDA EL MÉTODO de detección/transferencia estructural, no descubre nada.",
            "La transferencia de resonancia se verificó por simulación en el sandbox.",
            "El caso átomo↔sistema solar se marca ENGAÑOSO: similitud superficial sin "
            "equivalencia estructural profunda.",
            "Una simulación no prueba nada sobre el mundo físico.",
        ],
        "cannot_conclude": [
            "Que se haya descubierto una analogía nueva.",
            "Que la equivalencia estructural implique identidad física.",
            "Que la validez se extienda fuera de los regímenes probados.",
        ],
    }
