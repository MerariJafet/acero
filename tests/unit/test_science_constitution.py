"""CCC-11: scientific state ladder + constitution orchestrator (offline)."""

from __future__ import annotations

from acero.science.causal import CausalVerdict
from acero.science.claim_compiler import ClaimLevel, EvidenceProfile
from acero.science.constitution import (
    GovernanceInput,
    StatisticalControls,
    govern,
)
from acero.science.panel import Panelist, PanelVerdict, Review
from acero.science.preregistration import Regime
from acero.science.search_ledger import SearchSpaceLedger
from acero.science.states import (
    ACERO_CEILING,
    ScientificState,
    StateEvidence,
    acero_max_state,
    max_reachable,
)


def _full_controls():
    return StatisticalControls(
        effect_size=True, confidence_intervals=True, power_analysis=True,
        multiplicity_correction=True, sensitivity_analysis=True, outlier_check=True,
        residual_diagnostics=True, missing_data_handling=True, bootstrap_stability=True,
        leave_one_group_out=True, stopping_rules=True, exclusions_logged=True,
        heterogeneity=True, pipeline_uncertainty=True)


# --- state ladder --------------------------------------------------------
def test_state_ladder_stops_at_first_unmet():
    ev = StateEvidence(hypothesis_formulated=True, executed_with_null_test=True)
    assert max_reachable(ev) is ScientificState.EVIDENCIA_PRELIMINAR


def test_acero_ceiling_is_enforced():
    ev = StateEvidence(**{f: True for f in StateEvidence().__dict__})  # all true
    # even fully external-flagged, ACERO cannot claim past preprint candidate
    assert max_reachable(ev) is ScientificState.REPLICADO_EXTERNAMENTE
    assert acero_max_state(ev) is ACERO_CEILING


# --- constitution --------------------------------------------------------
def test_overclaim_blocks_advancement():
    prof = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    gi = GovernanceInput(prof, draft_text="esto demuestra que X causa Y",
                         controls=_full_controls(),
                         state_evidence=StateEvidence(hypothesis_formulated=True,
                                                      executed_with_null_test=True))
    rep = govern(gi)
    assert rep.overclaims and not rep.advance_permitted
    assert rep.allowed_claim_level is ClaimLevel.ASSOCIATION


def test_hard_panel_block_caps_state_and_halts():
    prof = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    panel = PanelVerdict([Review(Panelist.STATISTICIAN, "defectuoso",
                                 ["multiplicidad"], blocking=True),
                          Review(Panelist.DOMAIN_EXPERT, "prometedor")])
    gi = GovernanceInput(prof, draft_text="X asociado con Y", controls=_full_controls(),
                         panel=panel,
                         state_evidence=StateEvidence(hypothesis_formulated=True,
                                                      executed_with_null_test=True,
                                                      robust=True, protocol_frozen=True))
    rep = govern(gi)
    assert rep.panel_blocked and not rep.advance_permitted
    assert rep.acero_state <= ScientificState.RESULTADO_EXPLORATORIO_ROBUSTO


def test_missing_critical_controls_halts():
    prof = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    gi = GovernanceInput(prof, draft_text="X asociado con Y",
                         controls=StatisticalControls(effect_size=True))  # incomplete
    rep = govern(gi)
    assert rep.missing_controls and not rep.advance_permitted


def test_clean_result_advances():
    prof = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    ledg = SearchSpaceLedger()
    ledg.column("a")                          # tiny search space, low debt
    gi = GovernanceInput(
        prof, draft_text="X está asociado con Y en la población evaluada",
        controls=_full_controls(), search_ledger=ledg,
        causal=CausalVerdict(True, "identificable"),
        state_evidence=StateEvidence(hypothesis_formulated=True,
                                     executed_with_null_test=True))
    rep = govern(gi)
    assert rep.advance_permitted and not rep.overclaims
    assert rep.acero_state is ScientificState.EVIDENCIA_PRELIMINAR


def test_high_exploration_debt_is_flagged_in_discovery():
    prof = EvidenceProfile("X", "Y", Regime.DISCOVERY)
    ledg = SearchSpaceLedger()
    for i in range(30):
        ledg.column(f"c{i}")
    for t in ("log", "z", "rank", "box"):
        ledg.transform(t)
    gi = GovernanceInput(prof, draft_text="X asociado con Y", controls=_full_controls(),
                         search_ledger=ledg)
    rep = govern(gi)
    assert any("deuda de exploración" in r for r in rep.reasons)
