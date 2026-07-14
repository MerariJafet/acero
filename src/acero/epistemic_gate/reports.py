"""Human-readable rendering of gate results."""

from __future__ import annotations

from .models import GateResult

_ICON = {"PASS": "✅", "PASS_WITH_WARNINGS": "⚠️", "BLOCKED": "⛔",
         "ESCALATE_TO_HUMAN": "🧑‍⚖️", "BLOCKED_FOR_LEARNING": "📚"}


def render(result: GateResult) -> str:
    lines = [f"{_ICON.get(result.outcome.value, '?')} [{result.stage}] "
             f"{result.outcome.value}  "
             f"({len(result.passed_rules)}/{len(result.results)} rules passed)"]
    for b in result.blockers:
        lines.append(f"  ⛔ {b.rule_id}: {b.detail}")
        if b.remediation:
            lines.append(f"       → {b.remediation}")
    for w in result.warnings:
        tag = "cannot-evaluate" if not w.evaluable else "warning"
        lines.append(f"  ⚠️  [{tag}] {w.rule_id}: {w.detail}")
    return "\n".join(lines)


def render_pipeline(results: dict[str, GateResult]) -> str:
    return "\n".join(render(r) for r in results.values())
