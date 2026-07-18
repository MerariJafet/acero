"""Abstention Engine for the transit program.

Given the pipeline results, null tests, injection recovery and quality context,
decide whether ACERO may state the (bounded, non-discovery) claim or must ABSTAIN.
Every abstention records exactly which condition fired.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AbstentionDecision:
    abstain: bool
    reasons: list[str] = field(default_factory=list)
    verdict: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"abstain": self.abstain, "reasons": self.reasons, "verdict": self.verdict}


def decide(*, snr: float, period_agreement: dict[str, Any],
           period_stability_frac: float, null_summary: dict[str, Any],
           recovery_rate: float, quality_severe: bool,
           n_indistinguishable_candidates: int,
           thresholds: dict[str, Any]) -> AbstentionDecision:
    reasons: list[str] = []
    if snr < thresholds["detection_SNR"]:
        reasons.append(f"SNR {snr:.1f} < detection threshold {thresholds['detection_SNR']}")
    if not period_agreement.get("agree_1pct", False):
        reasons.append(
            f"pipelines disagree on period (frac_diff={period_agreement.get('frac_diff')})")
    if period_stability_frac > thresholds["period_stability_tol_frac"]:
        reasons.append(
            f"period unstable across detrending ({period_stability_frac:.3f} > "
            f"{thresholds['period_stability_tol_frac']})")
    if not null_summary.get("all_controlled", False):
        reasons.append(
            f"null tests not fully controlled (FPR={null_summary.get('false_positive_rate')})")
    if null_summary.get("false_positive_rate", 1.0) > thresholds["max_false_positive_rate"]:
        reasons.append("false-positive rate above allowed maximum")
    if recovery_rate < thresholds["min_recovery_for_claim"]:
        reasons.append(f"injection recovery {recovery_rate} below "
                       f"{thresholds['min_recovery_for_claim']}")
    if quality_severe:
        reasons.append("severe quality flags in the segment")
    if n_indistinguishable_candidates > 1:
        reasons.append(f"{n_indistinguishable_candidates} indistinguishable candidates")

    abstain = bool(reasons)
    verdict = ("ABSTAIN" if abstain
               else "RECOVERED_KNOWN_TRANSIT_UNDER_DECLARED_METHODS")
    return AbstentionDecision(abstain=abstain, reasons=reasons, verdict=verdict)
