"""Plural panel via Codex — injectable provider + honest fallback (offline)."""

from __future__ import annotations

from acero.portal.panel_review import PluralPanel, panel_verdict_to_record
from acero.science.panel import HARD_MANDATE, Panelist


class _FakeProvider:
    """Returns a canned per-persona review; the causalist (hard mandate) blocks."""
    def __init__(self, block_panelist_value=None):
        self.block = block_panelist_value
        self.calls = 0

    def available(self):
        return True

    def complete_json(self, prompt, schema, temperature=0.3):
        self.calls += 1
        # identify which persona this prompt is for
        who = next((p for p in Panelist if f"«{p.value}»" in prompt), None)
        blocking = who is not None and who.value == self.block
        return {"verdict": "defectuoso" if blocking else "prometedor",
                "objections": ["objeción de prueba"] if blocking else [],
                "blocking": blocking, "note": "ok"}


def test_panel_calls_all_eight_personas(monkeypatch):
    monkeypatch.delenv("ACERO_CRITIC_DISABLED", raising=False)
    prov = _FakeProvider()
    v = PluralPanel(provider=prov).review_context("un resultado", use_ai=True)
    assert prov.calls == 8 and len(v.reviews) == 8


def test_hard_mandate_block_is_detected(monkeypatch):
    monkeypatch.delenv("ACERO_CRITIC_DISABLED", raising=False)
    prov = _FakeProvider(block_panelist_value=Panelist.CAUSALIST.value)
    v = PluralPanel(provider=prov).review_context("resultado con confusión")
    assert v.blocked() and not v.consensus
    assert Panelist.CAUSALIST in HARD_MANDATE


def test_soft_mandate_block_does_not_halt(monkeypatch):
    monkeypatch.delenv("ACERO_CRITIC_DISABLED", raising=False)
    prov = _FakeProvider(block_panelist_value=Panelist.HOSTILE_WRITER.value)
    v = PluralPanel(provider=prov).review_context("resultado")
    # hostile writer objects but is not a hard mandate → no halt
    assert not v.blocked()


def test_fallback_when_disabled(monkeypatch):
    monkeypatch.setenv("ACERO_CRITIC_DISABLED", "1")
    v = PluralPanel(provider=_FakeProvider()).review_context("x", use_ai=True)
    assert len(v.reviews) == 8 and all("no disponible" in r.note for r in v.reviews)


def test_record_serialization_roundtrip(monkeypatch):
    monkeypatch.delenv("ACERO_CRITIC_DISABLED", raising=False)
    v = PluralPanel(provider=_FakeProvider()).review_context("x")
    rec = panel_verdict_to_record(v)
    assert len(rec["reviews"]) == 8 and "status" in rec and "blocked" in rec
