"""Term library, invariants, and regime tests."""
from __future__ import annotations

import numpy as np

from acero.inference.data.observations import generate
from acero.inference.discovery import change_points, invariants
from acero.inference.libraries.terms import TermLibrary


def test_library_rejects_reciprocal_when_crossing_zero():
    # harmonic x crosses zero -> 1/x rejected
    obs = generate("harmonic", seed=1, n=300, t_max=6.0)
    lib = TermLibrary.build(["x", "v"], obs.data, families={"poly", "reciprocal"})
    assert "1/x" not in lib.names
    assert any(e["term"] == "1/x" for e in lib.excluded)


def test_library_rejects_log_of_nonpositive():
    obs = generate("harmonic", seed=1, n=200, t_max=6.0)
    lib = TermLibrary.build(["x"], {"x": obs.data["x"]}, families={"poly", "log"})
    assert "log(x)" not in lib.names


def test_library_forbidden_terms_excluded():
    obs = generate("logistic", seed=1, n=200, t_max=6.0)
    lib = TermLibrary.build(["x"], obs.data, forbidden=["x^2"])
    assert "x^2" not in lib.names


def test_library_detects_algebraic_duplicates():
    # two identical columns -> one dropped
    x = np.linspace(1, 3, 100)
    lib = TermLibrary.build(["a", "b"], {"a": x, "b": x}, families={"poly"})
    # 'a' and 'b' are identical -> duplicate removed
    assert any("duplicate" in e["reason"] for e in lib.excluded)


def test_harmonic_energy_invariant_is_exact():
    obs = generate("harmonic", seed=1, n=600, t_max=10.0)
    lib = TermLibrary.build(["x", "v"], obs.data, max_complexity=2)
    theta, names = lib.theta(obs.data)
    invs = invariants.find_invariants(theta, names, top_k=2)
    assert invs and invs[0].classification in {"exact", "approximate"}
    # the conserved combination involves x^2 and v^2
    assert "x^2" in invs[0].combination and "v^2" in invs[0].combination


def test_constant_is_not_reported_as_invariant():
    obs = generate("damped", seed=1, n=400, t_max=8.0)
    lib = TermLibrary.build(["x", "v"], obs.data, max_complexity=2)
    theta, names = lib.theta(obs.data)
    for inv in invariants.find_invariants(theta, names, top_k=2):
        assert "1" not in inv.combination  # trivial constant excluded


def test_no_false_regime_on_periodic_data():
    obs = generate("harmonic", seed=1, n=500, t_max=10.0)
    lib = TermLibrary.build(["x", "v"], obs.data)
    theta, names = lib.theta(obs.data)
    cp = change_points.detect_change_points(obs.t, obs.data["x"], theta, names)
    assert cp["regime_change"] is False


def test_detects_real_regime_change():
    t = np.linspace(0, 10, 700)
    x = np.zeros_like(t)
    x[0] = 90.0
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        k = 0.3 if t[i] < 5 else 1.4
        x[i] = x[i - 1] + dt * (-k * x[i - 1])
    lib = TermLibrary.build(["x"], {"x": x})
    theta, names = lib.theta({"x": x})
    cp = change_points.detect_change_points(t, x, theta, names, n_windows=10, threshold=0.1)
    assert cp["regime_change"] is True
