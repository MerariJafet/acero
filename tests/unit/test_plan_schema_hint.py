"""P3: schema-awareness at PLAN time — the planner is told which columns a known table
already carries, so it never requests a redundant second table (the DR25 defect)."""
from __future__ import annotations

from acero.portal.experiment_factory import _known_schema_hint


def test_known_table_columns_injected_when_source_matches():
    exp = {"data_source": "NASA Exoplanet Archive tabla q1_q17_dr25_koi via TAP",
           "how": "regresión del valle", "what": "posición vs [Fe/H]"}
    hint = _known_schema_hint(exp)
    assert "koi_smet" in hint and "sin join" in hint
    assert "ESQUEMA CONOCIDO" in hint


def test_no_hint_for_unknown_source():
    assert _known_schema_hint({"data_source": "algún CSV genérico", "how": "", "what": ""}) == ""
