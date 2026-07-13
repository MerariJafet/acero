"""LLM provider abstraction.

Design rules:
  * Providers are interchangeable behind one interface.
  * Every call records model, version, temperature, and parameters (provenance).
  * LLM text is NEVER treated as scientific evidence — it is a drafting aid.
  * Paid providers are gated by policy and refuse to run unless explicitly enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    temperature: float
    params: dict = field(default_factory=dict)
    is_evidence: bool = False  # always False: model output is not evidence


class LLMProvider(Protocol):
    name: str

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = 1024) -> LLMResponse:
        ...
