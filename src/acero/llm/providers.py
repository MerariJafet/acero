"""Concrete LLM providers: deterministic mock, local Ollama, gated paid providers."""

from __future__ import annotations

import hashlib
import json

from ..core.errors import PolicyViolation
from ..policies.guard import PolicyGuard
from .base import LLMResponse


class MockProvider:
    """Deterministic, offline provider. Default in tests and this session.

    Produces a stable, inspectable pseudo-response derived from the prompt hash so
    behaviour is reproducible without any network or model.
    """

    name = "mock"

    def complete(
        self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024
    ) -> LLMResponse:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
        text = (
            f"[MOCK:{digest}] Deterministic placeholder response. "
            "This text is a drafting aid, NOT scientific evidence."
        )
        return LLMResponse(
            text=text, provider=self.name, model="mock-1",
            temperature=temperature, params={"max_tokens": max_tokens, "prompt_sha": digest},
        )


class OllamaProvider:
    """Local Ollama adapter. Active only if the daemon is reachable."""

    name = "ollama"

    def __init__(self, host: str = "http://127.0.0.1:11434", model: str = "llama3.1") -> None:
        self.host = host
        self.model = model

    def available(self) -> bool:  # pragma: no cover - depends on local daemon
        try:
            import httpx

            r = httpx.get(f"{self.host}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def complete(
        self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024
    ) -> LLMResponse:  # pragma: no cover - network/daemon gated
        import httpx

        payload = {
            "model": self.model, "prompt": prompt, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        r = httpx.post(f"{self.host}/api/generate", json=payload, timeout=120)
        r.raise_for_status()
        data = json.loads(r.text)
        return LLMResponse(
            text=data.get("response", ""), provider=self.name, model=self.model,
            temperature=temperature, params={"max_tokens": max_tokens},
        )


class PaidProvider:
    """Placeholder for Claude/OpenAI. Refuses unless policy enables paid services."""

    def __init__(self, name: str, guard: PolicyGuard) -> None:
        self.name = name
        self._guard = guard

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        if not self._guard.paid_llm_allowed():
            raise PolicyViolation(
                f"Paid provider '{self.name}' is disabled (external_paid_services=false). "
                "Human approval and a raised cost limit are required to enable it."
            )
        raise NotImplementedError(  # pragma: no cover
            f"'{self.name}' client intentionally not wired in this local-first build."
        )


def get_provider(name: str, guard: PolicyGuard | None = None, **kwargs):
    guard = guard or PolicyGuard()
    if name == "mock":
        return MockProvider()
    if name == "ollama":
        return OllamaProvider(
            host=kwargs.get("host", "http://127.0.0.1:11434"),
            model=kwargs.get("model", "llama3.1"),
        )
    if name in {"claude", "openai"}:
        return PaidProvider(name, guard)
    return MockProvider()
