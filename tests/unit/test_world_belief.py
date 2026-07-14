"""World Model belief-state tests."""

from __future__ import annotations

from acero.world_model.belief import BeliefPolicy, BeliefState


def test_no_evidence_gives_prior():
    b = BeliefState()
    assert abs(b.derive_confidence(BeliefPolicy()) - 0.2) < 1e-9


def test_single_datum_does_not_reach_certainty():
    b = BeliefState()
    b.apply(event="experiment", evidence=1.0, source="s1")
    assert b.confidence < 0.7  # smoothing + single-source penalty keep it modest


def test_confidence_never_reaches_one():
    b = BeliefState()
    for i in range(20):
        b.apply(event="experiment", evidence=5.0, replication=1, source=f"s{i}")
    assert b.confidence <= BeliefPolicy().max_confidence
    assert b.confidence < 1.0


def test_more_evidence_and_replication_increases_confidence():
    b = BeliefState()
    c1 = b.apply(event="experiment", evidence=1.0, source="s1")["confidence_after"]
    c2 = b.apply(event="experiment", evidence=1.0, replication=1, source="s2")["confidence_after"]
    assert c2 > c1


def test_counter_evidence_lowers_confidence():
    b = BeliefState()
    b.apply(event="experiment", evidence=2.0, source="s1")
    high = b.confidence
    b.apply(event="experiment", counter=3.0, source="s2")
    assert b.confidence < high


def test_contradiction_and_negative_penalise():
    b = BeliefState()
    b.apply(event="experiment", evidence=2.0, replication=1, source="s1")
    base = b.confidence
    b.apply(event="contradiction", contradiction=1)
    assert b.confidence < base


def test_history_is_versioned_and_reconstructable():
    b = BeliefState()
    b.apply(event="a", evidence=1.0, source="s1")
    b.apply(event="b", evidence=1.0, source="s2")
    assert len(b.history) == 2
    assert all("confidence_before" in h and "confidence_after" in h for h in b.history)
    # round-trip through serialisation preserves history
    b2 = BeliefState.from_dict(b.to_dict())
    assert len(b2.history) == 2
    assert abs(b2.confidence - b.confidence) < 1e-3  # 4-dp storage rounding


def test_distinct_sources_tracked():
    b = BeliefState()
    b.apply(event="e", evidence=1.0, source="same")
    b.apply(event="e", evidence=1.0, source="same")  # not distinct
    assert b.distinct_sources == 1
    b.apply(event="e", evidence=1.0, source="other")
    assert b.distinct_sources == 2


def test_policy_is_configurable():
    strict = BeliefPolicy(prior=0.0, single_source_penalty=0.5, max_confidence=0.5)
    b = BeliefState()
    b.apply(event="e", evidence=1.0, source="s1", policy=strict)
    assert b.confidence <= 0.5
