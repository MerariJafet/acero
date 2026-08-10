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
    """El guard de política protege a los proveedores DE PAGO por API. 'claude' dejó
    de serlo cuando se añadió ClaudeCliProvider (CLI local, cubierto por tu propia
    suscripción); el único que sigue siendo PaidProvider es 'openai'. El test apuntaba
    al proveedor equivocado y fallaba por razones cambiantes según hubiera sesión del
    CLI o no — nunca estaba probando el guard."""
    prov = get_provider("openai")
    with pytest.raises(PolicyViolation):
        prov.complete("anything")


def test_claude_cli_no_es_proveedor_de_pago():
    """Contraparte: 'claude' resuelve al CLI local, no al de pago. Si alguien lo
    vuelve a mapear a PaidProvider, este test lo delata."""
    from acero.llm.providers import ClaudeCliProvider
    assert isinstance(get_provider("claude"), ClaudeCliProvider)


def test_get_provider_defaults_to_mock():
    assert get_provider("unknown-name").name == "mock"
