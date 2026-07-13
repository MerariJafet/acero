from acero.epistemology.traffic_light import (
    EpistemicColor,
    EvidenceProfile,
    assess_color,
)
from acero.epistemology.types import EntityState, can_transition


def test_state_transitions_legal_and_illegal():
    assert can_transition(EntityState.DRAFT, EntityState.PROPOSED)
    assert can_transition(EntityState.TESTED, EntityState.REFUTED)
    assert not can_transition(EntityState.DRAFT, EntityState.SUPPORTED)  # skip
    assert not can_transition(EntityState.ARCHIVED, EntityState.ACTIVE)  # terminal


def test_traffic_light_black_when_refuted():
    a = assess_color(EvidenceProfile(refuted=True, supporting_evidence=5))
    assert a.color == EpistemicColor.BLACK


def test_traffic_light_red_for_speculation():
    a = assess_color(EvidenceProfile(is_speculation=True))
    assert a.color == EpistemicColor.RED


def test_traffic_light_red_without_provenance():
    a = assess_color(EvidenceProfile(supporting_evidence=3, has_provenance=False))
    assert a.color == EpistemicColor.RED


def test_traffic_light_yellow_when_not_reproduced():
    a = assess_color(EvidenceProfile(supporting_evidence=2, has_provenance=True, reproduced=False))
    assert a.color == EpistemicColor.YELLOW


def test_traffic_light_green_when_reproduced_and_clean():
    a = assess_color(
        EvidenceProfile(supporting_evidence=2, has_provenance=True, reproduced=True,
                        counter_evidence=0)
    )
    assert a.color == EpistemicColor.GREEN


def test_traffic_light_orange_when_counter_outweighs():
    a = assess_color(
        EvidenceProfile(supporting_evidence=1, counter_evidence=3, has_provenance=True)
    )
    assert a.color == EpistemicColor.ORANGE
