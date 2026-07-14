"""Exercises generated from REAL research artifacts.

Each exercise is grounded in an actual ACERO result (SINDy inference, the analogy, the
sunspot analysis). The solution is never shown before an attempt is recorded.
"""

from __future__ import annotations

from ..models import LearningExercise


class SolutionWithheldError(RuntimeError):
    """Raised when a solution is requested before an attempt exists."""


def build_exercise(concept: str, research_context: str, task: str, *,
                   difficulty: str = "medium",
                   prerequisites: list[str] | None = None,
                   expected_reasoning: list[str] | None = None,
                   rubric: list[str] | None = None, hints: list[str] | None = None,
                   solution: str = "", common_errors: list[str] | None = None,
                   transfer_task: str = "") -> LearningExercise:
    return LearningExercise(
        concept=concept, research_context=research_context, task=task,
        difficulty=difficulty, prerequisites=prerequisites or [],
        expected_reasoning=expected_reasoning or [], rubric=rubric or [],
        hints=hints or [], solution=solution, common_errors=common_errors or [],
        transfer_task=transfer_task)


def reveal_solution(exercise: LearningExercise, *, attempted: bool) -> str:
    """Return the worked solution only after an attempt was recorded."""
    if not attempted:
        raise SolutionWithheldError("attempt the exercise before viewing the solution")
    return exercise.solution


# A small library of real-artifact exercises used by the CLI and benchmark.
def sindy_exercises(project_id: str) -> list[LearningExercise]:
    return [
        build_exercise(
            "imposed_library", project_id,
            "The engine reported ẋ = -0.7x. Explain why this is NOT a discovered law.",
            expected_reasoning=["library was imposed", "fit not mechanism",
                                "level is system_identification"],
            rubric=["mentions imposed library", "distinguishes fit from law"],
            common_errors=["calling the recovered equation a law"],
            solution=("The polynomial term x was in a library we chose; STLSQ selected it "
                      "by fit. That is system identification, not a discovered law."),
            transfer_task="Do the same critique for a logistic-growth recovery."),
        build_exercise(
            "identifiability", project_id,
            "Given a near-singular ΘᵀΘ, is the coefficient unique? Why or why not?",
            expected_reasoning=["collinear columns", "many coefficient sets fit",
                                "non/partial identifiable"],
            rubric=["links condition number to non-uniqueness"],
            common_errors=["assuming a fit implies a unique parameter"],
            solution=("No: collinearity means many coefficient vectors fit equally well; "
                      "the parameter is non/partially identifiable."),
            transfer_task="Apply the same reasoning to logistic-growth parameters."),
        build_exercise(
            "noise", project_id,
            "Predict what happens to R²(dv/dt) as noise goes 0 → 0.1 in the damped system.",
            difficulty="medium",
            expected_reasoning=["derivatives amplify noise", "graceful degradation"],
            rubric=["predicts decreasing R²", "explains via derivative noise"],
            common_errors=["expecting abrupt failure"],
            solution="R² degrades smoothly (≈1.0 → ≈0.29) because derivative noise grows.",
            transfer_task="Predict the effect of irregular sampling on the same fit."),
    ]
