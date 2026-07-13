"""Policy enforcement. The single choke point for risky/costly actions.

Nothing in ACERO should activate a paid service, publish, or run unsafe code
without passing through a PolicyGuard check. Defaults are deny-by-policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.errors import PolicyViolation
from .loader import PolicyBundle, load_policies


@dataclass
class CostRequest:
    """A proposed action with an estimated cost, evaluated before it runs."""

    action: str
    estimated_cost_usd: float = 0.0
    request_count: int = 0
    download_mb: float = 0.0
    human_approved: bool = False


class PolicyGuard:
    def __init__(self, bundle: PolicyBundle | None = None) -> None:
        self.bundle = bundle or load_policies()

    # --- cost / circuit breaker ------------------------------------------
    def check_cost(self, req: CostRequest) -> None:
        costs = self.bundle.costs
        limits = costs.get("limits", {})
        breaker = costs.get("circuit_breaker", {})

        if req.estimated_cost_usd > 0 and not costs.get("flags", {}).get(
            "external_paid_services", False
        ):
            if not req.human_approved:
                raise PolicyViolation(
                    f"'{req.action}': paid action (${req.estimated_cost_usd}) blocked; "
                    "external_paid_services=false and no human approval."
                )

        max_run = limits.get("max_monetary_cost_usd_per_run", 0.0)
        if req.estimated_cost_usd > max_run and not req.human_approved:
            raise PolicyViolation(
                f"'{req.action}': cost ${req.estimated_cost_usd} exceeds per-run limit ${max_run}."
            )

        if breaker.get("enabled", True) and not req.human_approved:
            trip_cost = breaker.get("trip_on_estimated_cost_usd", 0.01)
            trip_req = breaker.get("trip_on_request_count", 1)
            if req.estimated_cost_usd >= trip_cost or req.request_count >= trip_req:
                raise PolicyViolation(
                    f"Circuit breaker tripped for '{req.action}' "
                    f"(cost=${req.estimated_cost_usd}, requests={req.request_count}). "
                    "Human approval required."
                )

        max_dl = limits.get("max_download_mb", 50)
        if req.download_mb > max_dl and not req.human_approved:
            raise PolicyViolation(
                f"'{req.action}': download {req.download_mb}MB exceeds limit {max_dl}MB."
            )

    # --- autonomy --------------------------------------------------------
    def action_level(self, action: str) -> str:
        actions = self.bundle.autonomy.get("actions", {})
        return actions.get(action, "human_required")

    def require_autonomous(self, action: str) -> None:
        """Raise unless the action is allowed to run automatically."""
        level = self.action_level(action)
        if level == "forbidden":
            raise PolicyViolation(f"Action '{action}' is forbidden by autonomy policy.")
        if level != "auto":
            raise PolicyViolation(
                f"Action '{action}' requires human approval (level={level})."
            )

    # --- research safety -------------------------------------------------
    def check_research_domain(self, domain: str) -> None:
        forbidden = self.bundle.research_safety.get("forbidden_domains", [])
        if domain in forbidden:
            raise PolicyViolation(
                f"Research domain '{domain}' is forbidden by research_safety policy."
            )

    # --- publication -----------------------------------------------------
    def check_publication(self, human_reviewed: bool) -> None:
        rules = self.bundle.publication.get("rules", {})
        if rules.get("automatic_publication", False) is False and not human_reviewed:
            raise PolicyViolation(
                "Publication/export requires human review (automatic_publication=false)."
            )

    def paid_llm_allowed(self) -> bool:
        return self.bundle.costs.get("flags", {}).get("external_paid_services", False)
