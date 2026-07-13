"""Build the configured LLM provider from Config + policy."""

from __future__ import annotations

from ..core.config import Config, get_config
from ..policies.guard import PolicyGuard
from .providers import get_provider


def provider_from_config(cfg: Config | None = None, guard: PolicyGuard | None = None):
    cfg = cfg or get_config()
    llm = cfg.llm
    return get_provider(
        llm.provider,
        guard=guard,
        command=llm.codex_command,
        model=llm.codex_model if llm.provider == "codex" else llm.ollama_model,
        sandbox=llm.codex_sandbox,
        host=llm.ollama_host,
    )
