"""Load and inject the research playbook — the program's accumulated wisdom.

Assimilates the lessons from the test period into every Codex prompt, so the
program researches at the frontier autonomously without human hand-holding.
"""

from __future__ import annotations

from pathlib import Path

_PLAYBOOK = (Path(__file__).parent / "research_playbook.md").read_text(encoding="utf-8")


def playbook() -> str:
    """Full playbook text."""
    return _PLAYBOOK


def brief(max_chars: int = 1400) -> str:
    """A compact prefix for prompts that can't take the whole thing."""
    return _PLAYBOOK[:max_chars]
