"""Tests for the JSONL parser and the advisory LLM skeptic (no real Codex calls)."""

from __future__ import annotations

from acero.experiment.llm_skeptic import LLMSkeptic
from acero.llm.providers import MockProvider, _parse_codex_jsonl


def test_parse_codex_jsonl_extracts_text_and_usage():
    stream = "\n".join([
        "Reading additional input from stdin...",
        '{"type":"thread.started","thread_id":"abc"}',
        '{"type":"turn.started"}',
        '{"type":"item.completed","item":{"id":"i0","type":"agent_message","text":"hello"}}',
        '{"type":"turn.completed","usage":{"input_tokens":100,"output_tokens":5}}',
        "garbled non-json line {",
    ])
    text, usage = _parse_codex_jsonl(stream)
    assert text == "hello"
    assert usage == {"input_tokens": 100, "output_tokens": 5}


def test_parse_codex_jsonl_handles_empty():
    text, usage = _parse_codex_jsonl("")
    assert text == "" and usage == {}


class _FakeStructuredProvider:
    """Stands in for CodexCliProvider without invoking the CLI (no cost)."""

    name = "fake-codex"

    def complete_json(self, prompt: str, schema: dict, *, temperature: float = 0.0) -> dict:
        return {"objections": [
            {"concern": "overfitting", "question": "Does it generalise?", "severity": "high"},
            {"concern": "range", "question": "Tested out of range?", "severity": "medium"},
        ]}


def test_llm_skeptic_with_structured_provider():
    sk = LLMSkeptic(_FakeStructuredProvider())
    assert sk.available()
    out = sk.review({"question": "Q"}, {"test_rmse": 0.9})
    assert out["available"] is True
    assert out["advisory"] is True
    assert out["is_evidence"] is False
    assert out["provider"] == "fake-codex"
    assert len(out["objections"]) == 2
    assert out["objections"][0]["concern"] == "overfitting"


def test_llm_skeptic_skips_provider_without_structured_output():
    # MockProvider has no complete_json -> skeptic returns advisory-empty, never errors.
    sk = LLMSkeptic(MockProvider())
    assert not sk.available()
    out = sk.review({"question": "Q"}, {"test_rmse": 0.9})
    assert out["available"] is False
    assert out["objections"] == []
    assert "note" in out
