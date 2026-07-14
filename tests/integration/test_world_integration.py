"""Integration: fold a discovery result into the World Model; ingest a dataset; viz."""

from __future__ import annotations

import math

import pytest

from acero.world_model.graph import WorldModel
from acero.world_model.ingest import ingest_exoplanets, kepler_test
from acero.world_model.nodes import NodeType
from acero.world_model.update import integrate_hidden_dynamics
from acero.world_model.viz import render_html


@pytest.fixture()
def wm(session_factory, ledger, project) -> WorldModel:
    return WorldModel(session_factory, ledger, project.id)


def _fake_report(system="damped_oscillator", winner="damped", hidden="damped"):
    return {
        "system": system, "hidden_family": hidden, "winner_family": winner, "seeds": [1, 2, 3],
        "eig_bits": 0.8, "reproduced": True, "poly9_extrapolation_rmse": 12345.0,
        "family_mean_test_rmse": {"mean": 20.0, "linear": 5.0, "exponential": 2.0,
                                  "damped": 0.5, "poly9": 0.9},
    }


def test_integrate_creates_beliefs_and_updates_confidence(wm):
    out = integrate_hidden_dynamics(wm, _fake_report())
    winner_node = wm.get_node(out["model_nodes"]["damped"])
    poly9_node = wm.get_node(out["model_nodes"]["poly9"])
    assert winner_node.confidence > poly9_node.confidence  # winner up, overfitter down
    assert wm.nodes(NodeType.EXPERIMENT)
    assert wm.nodes(NodeType.EVIDENCE)
    assert wm.nodes(NodeType.NEGATIVE_RESULT)


def test_integration_detects_stance_contradiction(wm):
    # damped(oscillatory) vs linear/exponential(monotonic) on same subject -> contradiction
    out = integrate_hidden_dynamics(wm, _fake_report())
    assert out["contradictions_created"] >= 1
    assert wm.nodes(NodeType.CONTRADICTION)


def test_model_recovery_mismatch_registers_anomaly(wm):
    out = integrate_hidden_dynamics(
        wm, _fake_report(winner="exponential", hidden="damped"))
    assert out["anomaly_id"] is not None
    assert wm.nodes(NodeType.ANOMALY)


# --- Kepler ingestion on a synthetic-but-Kepler-exact CSV (no network) ---
def _kepler_csv(tmp_path):
    rows = [("Earth", 1.0, 1.0), ("Venus", 0.72, 1.0), ("Jupiter", 5.2, 1.0),
            ("HotJup", 0.05, 0.9), ("SuperEarth", 0.15, 0.6), ("ColdGiant", 3.0, 1.3),
            ("TinyOrbit", 0.03, 0.8), ("WideOrbit", 8.0, 1.1)]
    lines = ["pl_name,pl_orbper,pl_orbsmax,st_mass"]
    for name, a, m in rows:
        p_yr = math.sqrt(a ** 3 / m)
        p_days = p_yr * 365.25
        lines.append(f"{name},{p_days:.6f},{a},{m}")
    p = tmp_path / "kepler.csv"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_kepler_test_recovers_slope_one(tmp_path):
    from acero.world_model.ingest import _parse_rows
    rows = _parse_rows(_kepler_csv(tmp_path).read_text())
    fit = kepler_test(rows)
    assert abs(fit["slope"] - 1.0) < 0.05
    assert fit["r2"] > 0.98
    assert fit["fraction_within_2x"] == 1.0


def test_ingest_exoplanets_updates_kepler_belief(wm, tmp_path):
    csv = _kepler_csv(tmp_path)
    out = ingest_exoplanets(wm, csv, manifest={"sha256": "sha256:test", "license": "public"})
    law = wm.get_node(out["law_id"])
    assert law.type == NodeType.LAW
    assert law.tested is True
    assert law.confidence > 0.2  # gained support from real-format data
    assert wm.nodes(NodeType.DATASET)
    assert wm.nodes(NodeType.OBSERVATION)


def test_viz_renders_html(wm):
    integrate_hidden_dynamics(wm, _fake_report())
    html = render_html(wm)
    assert "<svg" in html and "World Model" in html
    assert "Open contradictions" in html
