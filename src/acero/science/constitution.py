"""The Constitution — one orchestrator that ties the machinery into a governance verdict.

Given everything the CCC modules produce for a result — the search ledger, the protocol
registry, the causal audit, the independence ledger, the contribution score, the
uncertainty budget, the plural panel, and a draft dossier — this computes:

  * the regime (discovery vs confirmation),
  * the MAXIMUM claim the evidence permits (and any over-claims in the draft),
  * the highest scientific state ACERO may assign (bounded by its ceiling and by panel
    blocks),
  * whether the mandatory statistical controls are present,
  * and a single, honest ADVANCE / HOLD decision with reasons.

The whole point of the reviewer's critique is that being "interesting" is not enough.
This function is where "interesting" is forced to prove it is also *defensible*.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

from .causal import CausalVerdict
from .claim_compiler import ClaimLevel, EvidenceProfile, compile_claim, max_claim, scan_overclaims
from .contribution import ContributionReport
from .independence import IndependenceLedger
from .panel import PanelVerdict
from .preregistration import ProtocolRegistry, Regime
from .search_ledger import SearchSpaceLedger
from .states import ScientificState, StateEvidence, acero_max_state, next_required
from .uncertainty_budget import UncertaintyBudget


@dataclass
class StatisticalControls:
    """The reviewer's mandatory controls for every domain, as a computable checklist."""
    effect_size: bool = False
    confidence_intervals: bool = False
    power_analysis: bool = False
    multiplicity_correction: bool = False
    sensitivity_analysis: bool = False
    outlier_check: bool = False
    residual_diagnostics: bool = False
    missing_data_handling: bool = False
    bootstrap_stability: bool = False
    leave_one_group_out: bool = False
    stopping_rules: bool = False
    exclusions_logged: bool = False
    heterogeneity: bool = False
    pipeline_uncertainty: bool = False

    def missing(self) -> list[str]:
        return [f.name for f in fields(self) if not getattr(self, f.name)]

    def complete(self) -> bool:
        return not self.missing()

    # a minimal subset without which no numeric claim is even reportable
    _CRITICAL = ("effect_size", "confidence_intervals", "multiplicity_correction",
                 "exclusions_logged")

    def critical_missing(self) -> list[str]:
        return [c for c in self._CRITICAL if not getattr(self, c)]


@dataclass
class GovernanceInput:
    evidence_profile: EvidenceProfile
    draft_text: str = ""
    search_ledger: SearchSpaceLedger | None = None
    protocol_registry: ProtocolRegistry | None = None
    protocol_hash: str | None = None
    causal: CausalVerdict | None = None
    independence: IndependenceLedger | None = None
    contribution: ContributionReport | None = None
    uncertainty: UncertaintyBudget | None = None
    panel: PanelVerdict | None = None
    state_evidence: StateEvidence = field(default_factory=StateEvidence)
    controls: StatisticalControls = field(default_factory=StatisticalControls)


@dataclass
class GovernanceReport:
    regime: Regime
    allowed_claim_level: ClaimLevel
    allowed_claim: str
    overclaims: list[str]
    acero_state: ScientificState
    next_required: str
    contribution_band: str | None
    uncertainty_dominant: str | None
    panel_status: str
    panel_blocked: bool
    missing_controls: list[str]
    advance_permitted: bool
    reasons: list[str]

    def summary(self) -> dict[str, object]:
        return {
            "regime": self.regime.value,
            "allowed_claim": self.allowed_claim,
            "acero_state": self.acero_state.name,
            "next_required": self.next_required,
            "advance_permitted": self.advance_permitted,
            "panel_status": self.panel_status,
            "contribution_band": self.contribution_band,
            "uncertainty_dominant": self.uncertainty_dominant,
            "n_overclaims": len(self.overclaims),
            "critical_controls_missing": self.missing_controls,
            "reasons": self.reasons,
        }


def govern(gi: GovernanceInput) -> GovernanceReport:
    reasons: list[str] = []

    # 1) regime
    regime = Regime.DISCOVERY
    if gi.protocol_registry is not None and gi.protocol_hash:
        regime = gi.protocol_registry.classify(gi.protocol_hash)
    # a causal profile can only be causal if the audit says it's identifiable
    profile = gi.evidence_profile
    if gi.causal is not None and not gi.causal.allows_causal_language:
        reasons.append("causalidad no identificable → sin lenguaje causal")

    # 2) claim ceiling + over-claim scan
    lvl = max_claim(profile)
    claim = compile_claim(profile)
    overclaims = [f"{v.phrase} — {v.reason}" for v in scan_overclaims(gi.draft_text, profile)]
    if overclaims:
        reasons.append(f"{len(overclaims)} sobreafirmación(es) en el borrador")

    # 3) exploration debt without confirmation
    if gi.search_ledger is not None:
        debt = gi.search_ledger.debt_level()
        if debt in ("alta", "severa") and regime is Regime.DISCOVERY:
            reasons.append(f"deuda de exploración {debt} sin confirmación congelada")

    # 4) scientific state (bounded by ceiling and by panel blocks)
    state = acero_max_state(gi.state_evidence)
    panel_blocked = gi.panel is not None and gi.panel.blocked()
    if gi.panel is not None and panel_blocked:
        reasons.append("bloqueo del panel (mandato duro): "
                       + ", ".join(r.panelist.value for r in gi.panel.hard_blocks()))
        state = min(state, ScientificState.RESULTADO_EXPLORATORIO_ROBUSTO)
    panel_status = (gi.panel.summary()["status"] if gi.panel else "sin panel")

    # 5) mandatory statistical controls
    crit_missing = gi.controls.critical_missing()
    if crit_missing:
        reasons.append(f"controles estadísticos críticos ausentes: {crit_missing}")

    # 6) advancement decision
    advance = (not overclaims and not panel_blocked and not crit_missing
               and profile.has_null_test)
    if not profile.has_null_test:
        reasons.append("sin prueba nula → degradado, no avanza")
    if advance and not reasons:
        reasons.append("cumple los requisitos para el estado alcanzado")

    return GovernanceReport(
        regime=regime, allowed_claim_level=lvl, allowed_claim=claim,
        overclaims=overclaims, acero_state=state,
        next_required=next_required(gi.state_evidence),
        contribution_band=(gi.contribution.band if gi.contribution else None),
        uncertainty_dominant=(str(gi.uncertainty.report()["dominant_source"])
                              if gi.uncertainty else None),
        panel_status=str(panel_status), panel_blocked=panel_blocked,
        missing_controls=crit_missing, advance_permitted=advance, reasons=reasons)
