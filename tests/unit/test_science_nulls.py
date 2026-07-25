"""CCC-6: structure-preserving null catalog + recommender (offline, deterministic)."""

from __future__ import annotations

from acero.science.nulls import (
    DataStructure,
    NullFamily,
    block_permutation,
    circular_shift,
    label_permutation,
    plain_permutation_is_valid,
    recommend_null,
    subject_permutation,
)


def test_label_permutation_is_a_permutation_and_seeded():
    labels = list(range(20))
    a = label_permutation(labels, seed=1)
    assert sorted(a) == labels and a == label_permutation(labels, seed=1)
    assert a != labels                       # actually shuffled


def test_block_permutation_stays_within_blocks():
    labels = ["a", "b", "c", "d"]
    blocks = [0, 0, 1, 1]
    out = block_permutation(labels, blocks, seed=3)
    # each block's multiset is preserved (no cross-block movement)
    assert sorted(out[:2]) == ["a", "b"] and sorted(out[2:]) == ["c", "d"]


def test_subject_permutation_keeps_one_label_per_subject():
    # 2 subjects, 3 rows each; each subject has a single true label
    subject_of_row = ["s1", "s1", "s1", "s2", "s2", "s2"]
    subject_label = {"s1": 1, "s2": 0}
    out = subject_permutation(subject_of_row, subject_label, seed=0)
    # all rows of a subject share the same permuted label (no pseudoreplication)
    assert len(set(out[:3])) == 1 and len(set(out[3:])) == 1


def test_circular_shift_preserves_multiset():
    s = [1, 2, 3, 4, 5]
    assert circular_shift(s, 2) == [4, 5, 1, 2, 3]
    assert sorted(circular_shift(s, 2)) == s


def test_recommender_flags_temporal_and_group_structure():
    r_t = recommend_null(DataStructure(temporal=True))
    assert r_t.family is NullFamily.TEMPORAL_CIRCULAR and r_t.warnings
    r_g = recommend_null(DataStructure(has_groups=True))
    assert r_g.family is NullFamily.SUBJECT_PERMUTATION and r_g.warnings
    r_b = recommend_null(DataStructure(batch=True))
    assert r_b.family is NullFamily.BLOCK_PERMUTATION


def test_plain_permutation_valid_only_for_iid():
    assert plain_permutation_is_valid(DataStructure())
    assert not plain_permutation_is_valid(DataStructure(temporal=True))
    assert recommend_null(DataStructure()).family is NullFamily.LABEL_PERMUTATION
