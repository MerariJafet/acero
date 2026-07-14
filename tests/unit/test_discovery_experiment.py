"""Sprint 6 tests: experiment design, information gain, utility, stopping, critic."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from acero.discovery.experiment_critic import (
    CodexExperimentCritic,
    RuleBasedExperimentCritic,
)
from acero.discovery.experiment_design import (
    ExperimentProposal,
    NonDiscriminatingError,
    require_discriminating,
)
from acero.discovery.information_gain import (
    bayesian_eig,
    heuristic_eig,
    prior_sensitivity,
    uniform_prior,
)
from acero.discovery.research_utility import compute_utility, weight_sensitivity
from acero.discovery.stopping import DiscoveryState, StopDecision, evaluate


def _proposal(**over):
    base = dict(
        project_id="p", research_question="Q?", hypotheses_tested=["h1", "h2"],
        baseline="mean", positive_control="clean fit", negative_control="shuffled",
        metrics=["test_rmse"],
        preregistered_predictions={"h1": "monotonic", "h2": "oscillatory"},
        stopping_rules=["fixed seeds"],
    )
    base.update(over)
    return ExperimentProposal(**base)


def test_experiment_requires_two_hypotheses():
    with pytest.raises(ValidationError):
        _proposal(hypotheses_tested=["only_one"])


def test_discriminating_matrix_ok():
    matrix = require_discriminating(_proposal())
    assert matrix.is_discriminating


def test_non_discriminating_rejected():
    p = _proposal(preregistered_predictions={"h1": "monotonic", "h2": "monotonic"})
    with pytest.raises(NonDiscriminatingError):
        require_discriminating(p)


def test_rule_critic_blocks_missing_controls():
    p = _proposal(positive_control="", negative_control="")
    report = RuleBasedExperimentCritic().review(p)
    assert not report.ok
    assert any(i.concern == "missing_controls" for i in report.blocking)


def test_rule_critic_blocks_missing_baseline_and_metrics():
    p = _proposal(baseline="", metrics=[])
    report = RuleBasedExperimentCritic().review(p)
    concerns = {i.concern for i in report.blocking}
    assert "no_baseline" in concerns and "no_metrics" in concerns


def test_rule_critic_passes_valid():
    assert RuleBasedExperimentCritic().review(_proposal()).ok


def test_bayesian_eig_non_negative_and_bounded():
    hyps = ["a", "b", "c"]
    likel = {"a": {"x": 0.9, "y": 0.1}, "b": {"x": 0.5, "y": 0.5}, "c": {"x": 0.1, "y": 0.9}}
    res = bayesian_eig(uniform_prior(hyps), likel)
    assert 0.0 <= res.eig <= res.prior_entropy + 1e-9


def test_perfect_discrimination_gives_full_eig():
    # Two hypotheses, deterministic distinct outcomes -> EIG == 1 bit.
    likel = {"a": {"x": 1.0, "y": 0.0}, "b": {"x": 0.0, "y": 1.0}}
    res = bayesian_eig(uniform_prior(["a", "b"]), likel)
    assert abs(res.eig - 1.0) < 1e-6


def test_heuristic_eig_documented():
    res = heuristic_eig(8, 3)
    assert res.method == "heuristic"
    assert res.eig <= res.prior_entropy


def test_prior_sensitivity_reports_range():
    likel = {"a": {"x": 0.9, "y": 0.1}, "b": {"x": 0.1, "y": 0.9}}
    s = prior_sensitivity(likel, {"uniform": {"a": 0.5, "b": 0.5}, "skewed": {"a": 0.9, "b": 0.1}})
    assert s["range"] >= 0.0
    assert set(s["per_prior_eig"]) == {"uniform", "skewed"}


def test_utility_surfaces_components_not_just_number():
    b = compute_utility({"information_gain": 0.8, "compute_cost": 0.5})
    d = b.as_dict()
    assert "components" in d and "weights" in d
    assert d["weighted_benefit"] >= 0 and d["weighted_cost"] >= 0


def test_utility_cost_lowers_score():
    cheap = compute_utility({"information_gain": 0.8, "compute_cost": 0.0}).utility
    pricey = compute_utility({"information_gain": 0.8, "compute_cost": 1.0}).utility
    assert cheap > pricey


def test_weight_sensitivity_detects_instability():
    cands = {"a": {"information_gain": 0.9, "compute_cost": 0.1},
             "b": {"information_gain": 0.5, "compute_cost": 0.0}}
    variants = {"default": {"information_gain": 0.3, "compute_cost": 0.4},
                "cost_averse": {"information_gain": 0.1, "compute_cost": 0.9}}
    out = weight_sensitivity(cands, variants)
    assert "top_by_variant" in out and "stable_top_choice" in out


def test_stopping_rules_decisions():
    assert evaluate(DiscoveryState(budget_spent=2, budget_total=1)).decision == StopDecision.STOP
    assert evaluate(DiscoveryState(risk_exceeds_benefit=True)).decision == StopDecision.ESCALATE_TO_HUMAN
    assert evaluate(DiscoveryState(data_missing=True)).decision == StopDecision.PAUSE
    assert evaluate(DiscoveryState(inconclusive_streak=3)).decision == StopDecision.REFINE
    assert evaluate(DiscoveryState(has_discriminating_experiment=False)).decision == StopDecision.ESCALATE_TO_HUMAN
    assert evaluate(DiscoveryState(last_improvement=0.5, min_improvement=0.01)).decision == StopDecision.CONTINUE


class _FakeCritic:
    name = "codex"

    def complete_json(self, prompt, schema, *, temperature=0.0):
        return {"issues": [{"concern": "confound", "detail": "unmodelled variable", "severity": "high"}]}


def test_codex_critic_is_advisory_never_blocking():
    report = CodexExperimentCritic(_FakeCritic()).review(_proposal())
    assert report.source == "codex"
    assert report.ok  # advisory issues are never 'blocking'
    assert report.issues and report.issues[0].severity != "blocking"


def test_codex_critic_handles_bad_json():
    class Boom:
        def complete_json(self, prompt, schema, *, temperature=0.0):
            raise ValueError("no json")

    report = CodexExperimentCritic(Boom()).review(_proposal())
    assert report.source == "llm-error"
    assert report.ok
