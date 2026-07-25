"""EP4: rival hypotheses + discriminating tests + pre-research states (offline)."""

from __future__ import annotations

from acero.science.discrimination import (
    DiscriminatingTest,
    RivalSet,
    design_discriminating_test,
    rank_tests,
    shannon_entropy,
)
from acero.science.pre_research_states import (
    PreResearchEvidence,
    PreResearchState,
    max_reachable,
    ready_for_exploratory,
)


def _rivals():
    return RivalSet(
        question_id="q1", main="polaridad causa menor permeabilidad",
        null="sin efecto",
        rivals=("el tamaño molecular es el verdadero factor",
                "la lipofilia es el verdadero factor"),
        differential_predictions={
            "polaridad causa menor permeabilidad": "cae al ajustar por tamaño y lipofilia",
            "el tamaño molecular es el verdadero factor": "cae al ajustar por tamaño",
            "la lipofilia es el verdadero factor": "cae al ajustar por logD"})


def test_rival_set_is_well_posed():
    r = _rivals()
    assert r.n_hypotheses() == 4 and r.is_well_posed()


def test_entropy_maximal_for_uniform():
    assert abs(shannon_entropy([1, 1, 1, 1]) - 2.0) < 1e-9   # 4 hyps → 2 bits
    assert shannon_entropy([1, 0, 0]) == 0.0                  # certainty → 0 bits


def test_decisive_only_with_differential_outcomes():
    t = design_discriminating_test(_rivals(), required_data="descriptores + logD")
    assert t.decisive and t.expected_information_gain() > 0
    # a confirm-only test (all outcomes identical) is NOT decisive
    dull = DiscriminatingTest("t", "q", "solo confirma",
                              outcome_favors={"main": "efecto", "rival": "efecto"})
    assert not dull.decisive and dull.expected_information_gain() == 0.0


def test_rank_prefers_information_per_cost():
    cheap = design_discriminating_test(_rivals(), test_id="cheap")
    cheap.computational_cost = 0.1
    pricey = design_discriminating_test(_rivals(), test_id="pricey")
    pricey.experimental_cost = 0.9
    ranked = rank_tests([pricey, cheap])
    assert ranked[0].test_id == "cheap"


def test_pre_research_ladder_blocks_jump_to_research():
    ev = PreResearchEvidence(knowledge_mapped=True, claims_reconstructed=True)
    assert max_reachable(ev) is PreResearchState.CLAIMS_RECONSTRUCTED
    assert not ready_for_exploratory(ev)


def test_pre_research_ready_only_after_discriminating_test():
    ev = PreResearchEvidence(True, True, True, True, True, True, True)
    assert ready_for_exploratory(ev)
    assert max_reachable(ev) is PreResearchState.READY_FOR_EXPLORATORY_RESEARCH
