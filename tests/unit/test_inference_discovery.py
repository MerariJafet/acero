"""SINDy sparse identification, library, equivalence tests."""

from __future__ import annotations

import numpy as np

from acero.inference.data.derivatives import estimate, finite_difference, savgol_derivative
from acero.inference.data.observations import generate
from acero.inference.discovery.sparse_identification import (
    identify,
    stability_selection,
    threshold_sensitivity,
)
from acero.inference.libraries.terms import TermLibrary
from acero.inference.model_selection import equivalence


def _theta(obs):
    lib = TermLibrary.build(obs.variables, obs.data, max_complexity=2)
    return lib, *lib.theta(obs.data)


def test_recovers_logistic():
    obs = generate("logistic", seed=1, n=400, t_max=6.0)
    _, theta, names = _theta(obs)
    d = estimate(obs.t, obs.data["x"], method="finite_difference")
    eq = identify(theta, names, d.dydt, "dx/dt", threshold=0.1)
    # Structural recovery: the right two terms with the right signs (coefficient
    # magnitudes are approximate from finite-difference derivatives).
    assert "x" in eq.coefficients and "x^2" in eq.coefficients
    assert 0.6 < eq.coefficients["x"] < 0.95
    assert -0.12 < eq.coefficients["x^2"] < -0.04
    assert eq.r2 > 0.99


def test_recovers_damped_two_equations():
    obs = generate("damped", seed=1, n=500, t_max=8.0)
    _, theta, names = _theta(obs)
    dv = estimate(obs.t, obs.data["v"])
    eq = identify(theta, names, dv.dydt, "dv/dt", threshold=0.2)
    assert "x" in eq.coefficients and "v" in eq.coefficients
    assert abs(eq.coefficients["x"] + 4.0) < 0.1


def test_threshold_sensitivity_reported():
    obs = generate("exponential_decay", seed=1, n=400, t_max=6.0)
    _, theta, names = _theta(obs)
    d = estimate(obs.t, obs.data["x"])
    sens = threshold_sensitivity(theta, names, d.dydt)
    assert set(sens) == {"0.02", "0.05", "0.1", "0.2", "0.5"}
    # higher threshold -> fewer or equal active terms
    assert len(sens["0.5"]) <= len(sens["0.02"])


def test_stability_selection_prefers_true_term():
    obs = generate("exponential_decay", seed=1, n=400, t_max=6.0)
    _, theta, names = _theta(obs)
    d = estimate(obs.t, obs.data["x"])
    stab = stability_selection(theta, names, d.dydt, n_bootstrap=10)
    assert stab.get("x", 0) > 0.8  # the true term is stably selected


def test_noise_degrades_r2():
    clean = generate("damped", seed=2, n=500, t_max=8.0, noise=0.0)
    noisy = generate("damped", seed=2, n=500, t_max=8.0, noise=0.15)
    _, tc, nc = _theta(clean)
    _, tn, nn = _theta(noisy)
    r2_clean = identify(tc, nc, estimate(clean.t, clean.data["v"]).dydt, "dv/dt").r2
    r2_noisy = identify(tn, nn, estimate(noisy.t, noisy.data["v"], method="savgol").dydt, "dv/dt").r2
    assert r2_noisy < r2_clean


def test_finite_difference_flags_edges():
    t = np.linspace(0, 1, 50)
    y = t ** 2
    r = finite_difference(t, y)
    assert 0 in r.unreliable_index and len(y) - 1 in r.unreliable_index


def test_savgol_falls_back_gracefully():
    t = np.linspace(0, 1, 5)
    y = t ** 2
    r = savgol_derivative(t, y, window=51)  # window too big -> fallback
    assert r.dydt.shape == y.shape


def test_algebraic_equivalence_detected():
    a = {"x": 0.80, "x^2": -0.080}
    b = {"x": 0.802, "x^2": -0.079}
    c = {"x": 0.80, "x^3": -0.080}
    assert equivalence.algebraically_equivalent(a, b)
    assert not equivalence.algebraically_equivalent(a, c)


def test_out_of_sample_divergence():
    div = equivalence.divergence_region(lambda x: x, lambda x: x ** 2,
                                        np.linspace(0, 5, 50))
    assert div["diverges"]


def test_codex_proposed_terms_are_validated():
    # Codex proposals must pass parse/finite validation; garbage is rejected.
    import numpy as np

    from acero.inference.discovery.symbolic_search import validate_terms
    data = {"x": np.linspace(1, 3, 50), "v": np.linspace(-1, 1, 50)}
    proposed = [{"expression": "x*v", "rationale": "interaction"},
                {"expression": "sin(x)", "rationale": "oscillatory"},
                {"expression": "w**2", "rationale": "unknown symbol"},
                {"expression": "x +", "rationale": "unparseable"}]
    val = validate_terms(proposed, data)
    kept = {v["expression"] for v in val if v["valid"]}
    assert "x*v" in kept and "sin(x)" in kept
    assert "w**2" not in kept and "x +" not in kept
