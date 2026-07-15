"""Hard budget limits (Sprint 16).

Enforces per-program resource ceilings (CPU/GPU/RAM/storage/tokens/downloads/human-hours). A
charge that would exceed a limit is REFUSED — budgets are hard, not advisory. This composes
with the cost policy (paid services stay gated).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import BudgetUsage, ComputeBudget

_FIELDS = ("cpu_core_hours", "gpu_hours", "ram_gb", "storage_gb", "llm_tokens",
           "download_mb", "human_hours")


class BudgetExceeded(RuntimeError):
    def __init__(self, resource: str, requested: float, remaining: float) -> None:
        self.resource = resource
        super().__init__(f"budget exceeded for {resource}: need {requested}, "
                         f"{remaining} remaining")


@dataclass
class BudgetGuard:
    budget: ComputeBudget
    usage: BudgetUsage

    def remaining(self, resource: str) -> float:
        return float(getattr(self.budget, resource)) - float(getattr(self.usage, resource))

    def can_charge(self, resource: str, amount: float) -> bool:
        return amount <= self.remaining(resource) + 1e-9

    def charge(self, resource: str, amount: float) -> None:
        """Deduct from the budget; raise BudgetExceeded (no partial charge) if over."""
        if resource not in _FIELDS:
            raise ValueError(f"unknown budget resource {resource!r}")
        if not self.can_charge(resource, amount):
            raise BudgetExceeded(resource, amount, self.remaining(resource))
        setattr(self.usage, resource, getattr(self.usage, resource) + amount)

    def report(self) -> dict[str, dict[str, float]]:
        return {f: {"budget": float(getattr(self.budget, f)),
                    "used": float(getattr(self.usage, f)),
                    "remaining": self.remaining(f)} for f in _FIELDS}
