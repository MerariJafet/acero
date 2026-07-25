"""CCC-3: locked holdout, deterministic splits, group anti-leakage (offline)."""

from __future__ import annotations

import pytest

from acero.science.holdout import (
    HoldoutLockedError,
    HoldoutManager,
    group_split,
    random_split,
    temporal_split,
)
from acero.science.preregistration import FrozenAnalysisPlan, ProtocolRegistry


def _plan():
    return FrozenAnalysisPlan(
        hypothesis="h", primary_variable="v", population="p", inclusion_criteria="i",
        exclusion_criteria="e", variable_transform="t", statistical_model="m",
        primary_test="test", multiplicity_correction="BH", min_effect_size=0.1,
        decision_rule="r", failure_conditions="f")


def test_random_split_is_deterministic_and_partitions():
    keys = [f"row{i}" for i in range(200)]
    a = random_split(keys, 0.3, salt="s")
    b = random_split(keys, 0.3, salt="s")
    assert a.holdout_keys == b.holdout_keys                # reproducible
    assert a.discovery_keys | a.holdout_keys == set(keys)  # partition
    assert not (a.discovery_keys & a.holdout_keys)
    assert 0.2 < len(a.holdout_keys) / 200 < 0.4           # ~30%


def test_group_split_has_no_entity_leak():
    # 10 subjects, 5 rows each
    row_groups = {f"s{s}_r{r}": f"subj{s}" for s in range(10) for r in range(5)}
    split = group_split(row_groups, 0.3, salt="s")
    mgr = HoldoutManager(split, ProtocolRegistry(), row_groups)
    assert mgr.leaks() == []          # no subject on both sides
    # every row of a subject is on the same side
    disc_subj = {row_groups[k] for k in split.discovery_keys}
    hold_subj = {row_groups[k] for k in split.holdout_keys}
    assert not (disc_subj & hold_subj)


def test_temporal_split_holds_out_the_future():
    rows = {f"r{i}": float(i) for i in range(10)}
    split = temporal_split(rows, cutoff=7.0)
    assert split.holdout_keys == {"r7", "r8", "r9"}
    assert "r6" in split.discovery_keys


def test_holdout_is_locked_until_frozen_protocol():
    keys = [f"r{i}" for i in range(50)]
    split = random_split(keys, 0.3)
    reg = ProtocolRegistry()
    mgr = HoldoutManager(split, reg)
    # discovery always available
    assert mgr.discovery_keys() == split.discovery_keys
    # holdout locked without a protocol
    with pytest.raises(HoldoutLockedError):
        mgr.reveal_holdout("sha256:doesnotexist")
    # freeze → unblind works and is audited
    pre = reg.freeze(_plan())
    revealed = mgr.reveal_holdout(pre.hash)
    assert revealed == split.holdout_keys and mgr.is_revealed
    assert reg.unblindings(pre.hash)[0].dataset_ref == split.split_hash


def test_split_hash_stable_for_same_membership():
    keys = [f"r{i}" for i in range(30)]
    assert random_split(keys, 0.3, "s").split_hash == random_split(keys, 0.3, "s").split_hash
