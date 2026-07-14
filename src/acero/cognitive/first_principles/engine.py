"""First Principles Engine (Sprint 8.7): dimensional analysis, symmetries,
conservation, derivation verification, and constrained model search — tying the
verifiable pieces together and integrating with the World Model.
"""

from __future__ import annotations

from typing import Any

from ...world_model.graph import WorldModel
from ...world_model.nodes import NodeType
from .. import dimensions as dim
from . import model_search, symmetries
from .derivations import verify_derivation
from .models import FirstPrinciplesProblem, ModelType, ScientificDerivation


class FirstPrinciplesEngine:
    def __init__(self, wm: WorldModel | None = None) -> None:
        self.wm = wm

    # --- dimensional analysis ---
    def dimensional_analysis(self, problem: FirstPrinciplesProblem) -> dict[str, Any]:
        variables = {name: dim.named(d) for name, d in problem.variables.items()}
        groups = dim.buckingham_pi(variables)
        return {
            "n_variables": len(variables),
            "n_pi_groups": dim.n_pi_groups(variables),
            "pi_groups": [{k: str(v) for k, v in g.items()} for g in groups],
            "limitation": ("Dimensional analysis gives the SCALING / dimensionless "
                           "groups only. It does NOT determine the dimensionless constant "
                           "(e.g. the 2π in the pendulum period) — that needs the full "
                           "equations or an experiment."),
        }

    def validate_equation(self, lhs_dim: str, rhs_dim: str) -> dict[str, Any]:
        lhs, rhs = dim.named(lhs_dim), dim.named(rhs_dim)
        return {"consistent": dim.equation_consistent(lhs, rhs),
                "lhs": str(lhs), "rhs": str(rhs)}

    # --- symmetries & conservation ---
    def symmetry_conservation(self, symms: list[str]) -> list[dict[str, Any]]:
        return [symmetries.conservation_candidate(s) for s in symms]

    def check_conservation(self, model_conserves: list[str], required: list[str]) -> dict[str, Any]:
        return symmetries.check_conservation(model_conserves, required)

    # --- derivations ---
    def verify(self, derivation: ScientificDerivation) -> ScientificDerivation:
        result = verify_derivation(derivation)
        if self.wm is not None:
            self.wm.create(
                NodeType.DERIVATION, f"derivation: {result.target}",
                domain="physics",
                data={"derivation": result.model_dump(),
                      "confidence": result.confidence,
                      "unresolved_steps": result.unresolved_steps})
        return result

    # --- model search ---
    def search_models(self, x, y, specs: list[str], *, x_extra=None, y_extra=None
                      ) -> dict[str, Any]:
        cands = model_search.search(x, y, specs, x_extra=x_extra, y_extra=y_extra)
        minimal = model_search.select_minimal(cands)
        return {
            "candidates": [c.model_dump() for c in cands],
            "best_fit": cands[0].expression if cands else None,
            "minimal_model": minimal.expression if minimal else None,
            "observationally_equivalent": model_search.equivalent_models(cands),
            "distinguishing_experiment": model_search.distinguishing_experiment(cands),
        }

    # --- model classification: prediction is not explanation ---
    @staticmethod
    def classify(model_expr: str, *, mechanistic: bool, causal: bool,
                 hidden_variables: bool) -> dict[str, Any]:
        if causal:
            mtype = ModelType.CAUSAL
        elif mechanistic:
            mtype = ModelType.MECHANISTIC
        else:
            mtype = ModelType.PHENOMENOLOGICAL
        statements = []
        if not mechanistic and not causal:
            statements.append("predicts but does not explain")
        if hidden_variables:
            statements.append("depends on hidden variables")
        if mechanistic and not causal:
            statements.append("mechanistic in a regime, not necessarily fundamental")
        return {"model": model_expr, "type": mtype.value, "statements": statements,
                "note": "good prediction is not causal explanation"}
