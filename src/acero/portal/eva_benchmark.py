"""EVA/Question-Engine benchmark: does the specific (Codex) path actually beat the
heuristic, or just produce more text?

Metrics are decision-relevant, not verbosity: type-level distinctness across claims,
whether the CONFOUNDING vulnerability is surfaced, assumption specificity, and whether
questions reference the real claim instead of placeholders. Pure/offline given an
extractor — inject a Codex extractor for the live numbers, a fake one for tests.
"""

from __future__ import annotations

from typing import Any

from ..epistemic.eva import audit_external
from ..epistemic.vulnerability import VulnerabilityType
from ..questions.question_engine import question_from_vulnerability
from .epistemic_bridge import Extractor, _claim_from_hypothesis, heuristic_extract


def benchmark_extractor(hyps: list[dict[str, Any]],
                        extractor: Extractor | None) -> dict[str, Any]:
    """Score one extractor over a set of hypotheses. Higher is better for every metric
    except `duplicate_type_sets` (lower is better)."""
    type_sets, content_sets, all_assumptions = [], [], 0
    confounding, generic_q, total_q = 0, 0, 0
    for h in hyps:
        claim, _prov, _conf = _claim_from_hypothesis(h, [], extractor=extractor)
        vulns = audit_external(claim).vulnerabilities
        type_sets.append(frozenset(v.type.value for v in vulns))
        # content signature = type + wording; rivals share types but not wording
        content_sets.append(frozenset(
            f"{v.type.value}:{(v.description or '')[:60]}" for v in vulns))
        all_assumptions += sum(1 for v in vulns
                               if v.type == VulnerabilityType.UNVALIDATED_ASSUMPTION)
        if VulnerabilityType.CONFOUNDING in {v.type for v in vulns}:
            confounding += 1
        for v in vulns:                       # question genericity on every vulnerability
            q = question_from_vulnerability(v, claim).question_text
            total_q += 1
            if "la exposición" in q or "el outcome" in q:
                generic_q += 1
    n = len(hyps) or 1

    def _distinct(sets: list) -> float:
        seen: dict[Any, int] = {}
        for s in sets:
            seen[s] = seen.get(s, 0) + 1
        dup = sum(c for c in seen.values() if c > 1)
        return round(1 - dup / n, 3)

    return {
        "n_claims": len(hyps),
        # type-set distinctness is a WEAK proxy: rival claims legitimately share types.
        "type_distinctness": _distinct(type_sets),
        # content distinctness (type + wording) is the real specificity signal.
        "content_distinctness": _distinct(content_sets),
        "confounding_coverage": round(confounding / n, 3),
        "assumption_vulns_per_claim": round(all_assumptions / n, 2),
        "generic_question_rate": round(generic_q / (total_q or 1), 3),
    }


def compare(hyps: list[dict[str, Any]],
            codex_extractor: Extractor | None) -> dict[str, Any]:
    """Heuristic vs Codex-specific EVA on the same hypotheses."""
    return {
        "heuristic": benchmark_extractor(hyps, heuristic_extract),
        "codex": benchmark_extractor(hyps, codex_extractor) if codex_extractor else None,
    }
