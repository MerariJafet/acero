import pytest

from acero.core.errors import PolicyViolation
from acero.llm.providers import MockProvider, get_provider


def test_mock_provider_is_deterministic():
    p = MockProvider()
    a = p.complete("same prompt")
    b = p.complete("same prompt")
    assert a.text == b.text
    assert a.is_evidence is False  # model output is never evidence


def test_mock_provider_records_params():
    r = MockProvider().complete("hi", temperature=0.2, max_tokens=50)
    assert r.provider == "mock"
    assert r.model == "mock-1"
    assert r.params["max_tokens"] == 50


def test_paid_provider_refuses_without_policy():
    prov = get_provider("claude")
    with pytest.raises(PolicyViolation):
        prov.complete("anything")


def test_get_provider_defaults_to_mock():
    assert get_provider("unknown-name").name == "mock"
