"""CCC-10: plural adversarial panel — disagreement preserved, hard blocks halt (offline)."""

from __future__ import annotations

from acero.science.panel import (
    MANDATES,
    Panelist,
    Review,
    run_panel,
)


def _all_agree_fn(panelist, ctx):
    return Review(panelist, "prometedor")


def _one_dissenter_fn(panelist, ctx):
    if panelist is Panelist.CAUSALIST:
        return Review(panelist, "defectuoso",
                      objections=["confusión no controlada"], blocking=True)
    return Review(panelist, "solido")


def _soft_dissent_fn(panelist, ctx):
    if panelist is Panelist.HOSTILE_WRITER:
        return Review(panelist, "debil", objections=["abstract excede"], blocking=True)
    return Review(panelist, "prometedor")


def test_eight_panelists_with_mandates():
    assert len(list(Panelist)) == 8
    assert all(p in MANDATES for p in Panelist)


def test_consensus_only_when_all_agree():
    v = run_panel({}, _all_agree_fn)
    assert v.consensus and v.disagreement == 1 and v.summary()["status"] == "consenso"


def test_disagreement_is_preserved_not_averaged():
    v = run_panel({}, _one_dissenter_fn)
    assert not v.consensus and v.disagreement == 2
    assert v.worst_verdict() == "defectuoso"       # not smoothed to the majority


def test_hard_mandate_block_halts_advancement():
    v = run_panel({}, _one_dissenter_fn)          # causalist (hard) blocks
    assert v.blocked() and Panelist.CAUSALIST.value in v.summary()["hard_blocks"]


def test_soft_block_does_not_halt():
    v = run_panel({}, _soft_dissent_fn)           # hostile writer (soft) objects
    assert v.blocking_objections() and not v.blocked()   # not a HARD mandate


def test_run_panel_asks_every_panelist_independently():
    seen = []

    def fn(p, ctx):
        seen.append(p)
        return Review(p, "prometedor")
    run_panel({}, fn)
    assert set(seen) == set(Panelist)
