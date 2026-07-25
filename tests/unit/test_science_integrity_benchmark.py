"""L2: integrity benchmark — governance must cut false positives to ~0 (offline)."""

from __future__ import annotations

from acero.science.integrity_benchmark import build_cases, evaluate


def test_cases_cover_the_main_flaws():
    flaws = {c.flaw for c in build_cases()}
    for f in ("overclaim", "no_null", "p_hacking", "confounding", "leakage",
              "no_controls", "false_novelty"):
        assert f in flaws


def test_governance_eliminates_false_positives():
    rep = evaluate()
    # without governance every indefensible positive is advanced (100% FP)
    assert rep.fpr_without == 1.0
    # with governance, no indefensible positive is advanced
    assert rep.with_gov_false_positives == 0
    assert rep.fpr_with == 0.0
    assert rep.summary()["reduccion_FP"] == 1.0


def test_governance_does_not_block_defensible_cases():
    rep = evaluate()
    # the genuinely clean cases are NOT wrongly blocked (no false negatives)
    assert rep.with_gov_false_negatives == 0


def test_every_indefensible_case_has_a_reason():
    rep = evaluate()
    for row in rep.per_case:
        if not row["defendible"]:
            assert not row["con_gob_avanza"] and row["razones"]
