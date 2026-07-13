import pytest

from acero.core.config import load_config
from acero.core.errors import PolicyViolation
from acero.policies.guard import CostRequest, PolicyGuard
from acero.policies.loader import REQUIRED_POLICIES, load_policies


def test_all_policies_load():
    bundle = load_policies()
    for name in REQUIRED_POLICIES:
        assert name in bundle.policies
        assert bundle.policies[name]["policy"] == name


def test_config_defaults_and_db_url():
    cfg = load_config(env="development")
    assert cfg.app.name == "ACERO"
    assert cfg.abs_db_url().startswith("sqlite:////")  # absolute path resolved


def test_paid_llm_disabled_by_default():
    guard = PolicyGuard()
    assert guard.paid_llm_allowed() is False


def test_cost_guard_blocks_paid_action():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_cost(CostRequest(action="call_gpt", estimated_cost_usd=0.5))


def test_cost_guard_circuit_breaker_trips_on_first_request():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_cost(CostRequest(action="paid_call", request_count=1))


def test_cost_guard_allows_zero_cost_local_action():
    guard = PolicyGuard()
    guard.check_cost(CostRequest(action="local_compute", estimated_cost_usd=0.0))


def test_autonomy_forbidden_and_required():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.require_autonomous("activate_paid_llm")  # forbidden
    with pytest.raises(PolicyViolation):
        guard.require_autonomous("git_push")  # human_required
    guard.require_autonomous("run_sandboxed_code")  # auto -> no raise


def test_research_domain_guard():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_research_domain("wet_lab_biology")
    guard.check_research_domain("mathematical_modeling")  # allowed


def test_publication_requires_human_review():
    guard = PolicyGuard()
    with pytest.raises(PolicyViolation):
        guard.check_publication(human_reviewed=False)
    guard.check_publication(human_reviewed=True)
