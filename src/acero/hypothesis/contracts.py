"""Agent contracts (Protocols) for the ACERO research agents.

Sprints 1–4 implement rule-based, deterministic versions of the agents that the
pilot needs (Skeptic, and an explicit Hypothesis builder in the orchestrator).
These Protocols define the interfaces the fuller LLM-backed agents (Sprints 5+)
must satisfy, so the science stays in verifiable services rather than in prompts.

Every agent that uses an LLM must record the prompt version and model parameters
(provenance); LLM text is never treated as scientific evidence.
"""

from __future__ import annotations

from typing import Any, Protocol


class HypothesisGenerator(Protocol):
    """Produces competing, falsifiable hypotheses for a question."""

    prompt_version: str

    def generate(self, question: str, *, n: int = 3) -> list[dict[str, Any]]:
        """Return hypotheses, each with statement, assumptions, falsification_criteria."""
        ...


class Skeptic(Protocol):
    """Attempts to refute an experiment's conclusion."""

    def review(self, prereg: dict[str, Any], run_record: dict[str, Any],
               metrics: dict[str, Any]) -> dict[str, Any]:
        ...


class Methodologist(Protocol):
    """Turns a question into an experiment design (variables, controls, metric)."""

    def design(self, question: str, hypotheses: list[str]) -> dict[str, Any]:
        ...


class NoveltyReviewer(Protocol):
    """Compares against prior art. Never certifies absolute novelty."""

    def assess(self, claim: str, prior_art: list[dict[str, Any]]) -> dict[str, Any]:
        ...


class Tutor(Protocol):
    """Explains intuition/math/code and checks human understanding."""

    def explain(self, topic: str, level: str = "intuition") -> str:
        ...
