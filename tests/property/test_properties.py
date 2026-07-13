"""Property-based tests (Hypothesis) for invariants."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from acero.core.hashing import hash_json
from acero.core.ids import is_valid, new_id
from acero.epistemology.traffic_light import EvidenceProfile, assess_color
from acero.epistemology.types import STATE_TRANSITIONS, EntityState, can_transition

_PREFIXES = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


@given(prefix=_PREFIXES, ms=st.integers(min_value=0, max_value=10**13))
def test_generated_ids_always_valid(prefix, ms):
    i = new_id(prefix, now_ms=ms, entropy=b"\x00" * 10)
    assert is_valid(i, prefix)


@given(a=st.integers(min_value=0, max_value=10**12), b=st.integers(min_value=0, max_value=10**12))
def test_id_time_ordering(a, b):
    ia = new_id("x", now_ms=min(a, b), entropy=b"\x00" * 10)
    ib = new_id("x", now_ms=max(a, b), entropy=b"\x00" * 10)
    assert ia <= ib


@given(
    d=st.dictionaries(
        st.text(min_size=1, max_size=5),
        st.integers() | st.text(max_size=5) | st.booleans(),
        max_size=6,
    )
)
def test_hash_json_order_independent(d):
    items = list(d.items())
    reordered = dict(reversed(items))
    assert hash_json(d) == hash_json(reordered)


@given(src=st.sampled_from(list(EntityState)), dst=st.sampled_from(list(EntityState)))
def test_transition_matches_table(src, dst):
    assert can_transition(src, dst) == (dst in STATE_TRANSITIONS.get(src, set()))


@given(
    sup=st.integers(min_value=0, max_value=10),
    cnt=st.integers(min_value=0, max_value=10),
    prov=st.booleans(),
    repro=st.booleans(),
)
def test_traffic_light_total_and_deterministic(sup, cnt, prov, repro):
    p = EvidenceProfile(supporting_evidence=sup, counter_evidence=cnt,
                        has_provenance=prov, reproduced=repro)
    a1 = assess_color(p)
    a2 = assess_color(p)
    assert a1.color == a2.color  # deterministic
    assert a1.color is not None   # always assigns a colour (total function)


@given(refuted=st.booleans(), retracted=st.booleans())
def test_refuted_or_retracted_is_black(refuted, retracted):
    from acero.epistemology.traffic_light import EpistemicColor

    p = EvidenceProfile(supporting_evidence=5, has_provenance=True, reproduced=True,
                        refuted=refuted, retracted=retracted)
    a = assess_color(p)
    if refuted or retracted:
        assert a.color == EpistemicColor.BLACK
