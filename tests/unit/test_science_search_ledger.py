"""CCC-2: search-space ledger and exploration debt (offline, deterministic)."""

from __future__ import annotations

from acero.science.preregistration import (
    FrozenAnalysisPlan,
    ProtocolRegistry,
    Regime,
)
from acero.science.search_ledger import Axis, SearchSpaceLedger


def test_effective_comparisons_multiplies_forking_axes():
    lg = SearchSpaceLedger(mission_id="m1")
    for c in ("gene_a", "gene_b", "gene_c"):      # 3 columns
        lg.column(c)
    lg.transform("log"); lg.transform("zscore")   # 2 transforms
    lg.model("ols"); lg.model("mixed")            # 2 models
    lg.metric("p=0.01")                           # a peek, not a fork
    # 3 * 2 * 2 = 12 effective comparisons
    assert lg.effective_comparisons() == 12
    assert lg.debt_level() == "moderada"
    assert lg.suggested_alpha(0.05) < 0.05


def test_distinct_dedupes_repeated_choices():
    lg = SearchSpaceLedger()
    lg.column("x"); lg.column("x"); lg.column("y")
    assert lg.distinct(Axis.COLUMN) == 2


def test_decisions_after_seeing_data_force_exploratory():
    lg = SearchSpaceLedger()
    lg.mark_data_seen()
    lg.subset("solo mujeres tras ver señal")   # recorded as after_seeing_data
    reg, why = lg.classify_result()
    assert reg is Regime.DISCOVERY and "exploratorio" in why
    assert lg.decisions_after_data() >= 1


def test_confirmation_requires_frozen_unblinded_protocol():
    lg = SearchSpaceLedger()
    reg_store = ProtocolRegistry()
    plan = FrozenAnalysisPlan(
        hypothesis="h", primary_variable="v", population="p",
        inclusion_criteria="i", exclusion_criteria="e", variable_transform="t",
        statistical_model="m", primary_test="test", multiplicity_correction="BH",
        min_effect_size=0.1, decision_rule="r", failure_conditions="f")
    pre = reg_store.freeze(plan)
    # frozen but not unblinded → still exploratory
    assert lg.classify_result(reg_store, pre.hash)[0] is Regime.DISCOVERY
    reg_store.unblind(pre.hash, "holdout")
    assert lg.classify_result(reg_store, pre.hash)[0] is Regime.CONFIRMATION


def test_empty_ledger_has_no_debt():
    lg = SearchSpaceLedger()
    assert lg.effective_comparisons() == 1 and lg.debt_level() == "ninguna"


def test_summary_shape():
    lg = SearchSpaceLedger(mission_id="m")
    lg.column("a"); lg.model("ols")
    s = lg.summary()
    assert s["effective_comparisons"] == 1 or s["effective_comparisons"] >= 1
    assert set(("degrees_of_freedom", "exploration_debt", "decisions_after_data")) <= s.keys()
