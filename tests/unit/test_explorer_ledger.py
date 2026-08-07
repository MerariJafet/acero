"""Tests for the ExplorerLedger — the program's memory of what worked."""

from __future__ import annotations

from acero.science.explorer_ledger import ExplorerLedger, _norm


def test_norm_ignores_case_punctuation_and_spacing():
    assert _norm("  Área  del CÍRCULO, radio r! ") == "área del círculo radio r"


def test_record_and_recall_roundtrip(tmp_path):
    led = ExplorerLedger(store=tmp_path / "l")
    led.record("suma de Gauss", {"status": "settled", "verdict": "verified",
                                  "hypothesis": "n(n+1)/2",
                                  "viable_approaches": [{"method": "induccion",
                                                         "candidate": "n(n+1)/2",
                                                         "tools_used": ["sym_sum"]}]})
    r = led.recall("Suma de Gauss")           # case/spacing-insensitive
    assert r and r["verdict"] == "verified"
    # a fresh ledger on the same store reloads it (persisted)
    assert ExplorerLedger(store=tmp_path / "l").recall("suma de gauss")["hypothesis"] == "n(n+1)/2"


def test_hints_surface_prior_working_paths(tmp_path):
    led = ExplorerLedger(store=tmp_path / "l")
    led.record("objetivo x", {"verdict": "verified",
                              "viable_approaches": [{"method": "algebra", "candidate": "F",
                                                     "tools_used": ["sym_sum"]}]})
    h = led.hints("objetivo x")
    assert "YA FUNCIONARON" in h and "algebra" in h and "sym_sum" in h
    assert led.hints("objetivo nunca visto") == ""


def test_stronger_verdict_is_not_overwritten_by_weaker(tmp_path):
    led = ExplorerLedger(store=tmp_path / "l")
    led.record("g", {"verdict": "verified", "viable_approaches": []})
    led.record("g", {"verdict": "holds_empirically", "viable_approaches": []})
    assert led.recall("g")["verdict"] == "verified"   # keeps the strongest


def test_in_memory_store_never_writes(tmp_path):
    led = ExplorerLedger(store=None)
    led.record("g", {"verdict": "candidate", "viable_approaches": []})
    assert led.recall("g")["verdict"] == "candidate"
    assert not list(tmp_path.iterdir())               # nothing written anywhere
