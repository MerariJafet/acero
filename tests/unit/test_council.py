"""Tests for El Consejo — persona council data + per-project progress."""

from __future__ import annotations

from acero.portal.council import PERSONAS, STAGES, council_for


def test_all_personas_placed_in_a_stage():
    placed = {pid for st in STAGES for pid in st["ids"]}
    assert placed == {p["id"] for p in PERSONAS}
    assert len(PERSONAS) == 14


def test_empty_project_falls_back_to_maturity():
    c = council_for({})
    assert len(c["personas"]) == 14
    assert all(p["source"] == "maturity" for p in c["personas"])
    assert all(0 <= p["progress"] <= 100 for p in c["personas"])
    # a 'good' persona baselines higher than a 'warn' one
    prog = {p["id"]: p["progress"] for p in c["personas"]}
    assert prog["davinci"] > prog["gauss"]


def test_real_kpis_drive_project_signal():
    c = council_for({"hypotheses": 6, "experiments": 5, "approved": 3, "dossiers": 1})
    prog = {p["id"]: p for p in c["personas"]}
    assert prog["davinci"]["source"] == "project"        # experiments → Da Vinci
    assert prog["hilbert"]["source"] == "project"         # hypotheses → Hilbert
    assert prog["davinci"]["progress"] == min(100, 5 * 13)
    assert prog["gauss"]["progress"] == min(100, 1 * 24)
    assert 0 <= c["overall"] <= 100


def test_verdicts_pass_through_capped():
    v = [{"title": f"h{i}", "verdict": "verified", "status": "good"} for i in range(9)]
    c = council_for({"hypotheses": 1}, verdicts=v)
    assert len(c["verdicts"]) == 6


def test_persona_shows_its_real_ledger_items():
    """U2: each owner-persona surfaces its real fichas from the project ledger."""
    items = {
        "candidate": [{"claim": "phi(n) no divide n-1"}],
        "experiment": [{"claim": "Lehmer", "result": {"verdict": "holds_empirically"},
                        "method": "Popper"}],
        "literature": [{"title": "Lehmer's totient problem", "year": 1932}],
        "dossier": [], "critique": [],
    }
    c = council_for({"hypotheses": 1, "experiments": 1}, items=items)
    by = {p["id"]: p for p in c["personas"]}
    # Popper owns experiments → his ficha carries the verdict
    assert by["popper"]["items_label"] == "experimentos"
    assert by["popper"]["items"][0]["verdict"] == "holds_empirically"
    # Hilbert owns hypotheses, Hipatia literature
    assert by["hilbert"]["items"][0]["title"].startswith("phi(n)")
    assert by["hipatia"]["items"][0]["title"] == "Lehmer's totient problem"
    # a non-owner persona has no items panel
    assert "items_label" not in by["davinci"]
