"""Static screening of code before execution (defense in depth).

The sandbox isolates at runtime, but we also refuse obviously dangerous code up
front so a reviewer can see the intent was checked. Screening is conservative and
pattern-based; it is NOT a substitute for the runtime isolation in runner.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..policies.loader import PolicyBundle, load_policies


@dataclass
class ScreenResult:
    allowed: bool
    matches: list[str]

    @property
    def reason(self) -> str:
        if self.allowed:
            return "No forbidden patterns detected."
        return "Refused; forbidden patterns: " + ", ".join(self.matches)


def screen_code(code: str, bundle: PolicyBundle | None = None) -> ScreenResult:
    bundle = bundle or load_policies()
    patterns = bundle.execution.get("forbidden_patterns", [])
    lowered = code
    found = [p for p in patterns if p in lowered]
    return ScreenResult(allowed=not found, matches=found)
