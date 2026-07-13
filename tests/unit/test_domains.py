import math

import pytest

from acero.domains.registry import all_plugins, get_plugin, plugin_names, run_all_benchmarks


def test_all_four_domains_present():
    assert plugin_names() == ["astronomy", "chemistry", "genetics", "physics"]


@pytest.mark.parametrize("name", ["physics", "astronomy", "genetics", "chemistry"])
def test_domain_benchmarks_pass(name):
    r = get_plugin(name).benchmark()
    assert r.all_passed, [c.name for c in r.cases if not c.passed]


def test_run_all_benchmarks():
    res = run_all_benchmarks()
    assert all(r["all_passed"] for r in res.values())
    assert sum(r["total"] for r in res.values()) >= 12


def test_plugin_info_declares_no_wet_lab():
    for p in all_plugins():
        info = p.info()
        assert info["wet_lab"] is False
        assert info["simulators"]
        assert info["risks"]


# --- physics ---
def test_physics_projectile_and_validation():
    phys = get_plugin("physics")
    out = phys.simulate("projectile_range", {"v0": 20, "angle_deg": 30})
    assert out["range_m"] > 0
    assert not phys.validate("projectile", {"angle_deg": 120}).ok
    assert not phys.validate("mechanics", {"m": -1}).ok


# --- astronomy ---
def test_astronomy_kepler():
    astro = get_plugin("astronomy")
    assert math.isclose(astro.simulate("kepler_period", {"a_au": 1.0})["period_yr"], 1.0)
    assert not astro.validate("orbit", {"a_au": -1}).ok


# --- genetics ---
def test_genetics_translate_and_validation():
    gen = get_plugin("genetics")
    assert gen.simulate("translate", {"sequence": "ATGAAATAA"})["protein"] == "MK"
    assert gen.simulate("transcribe", {"sequence": "ATGC"})["rna"] == "AUGC"
    assert not gen.validate("dna", {"sequence": "ATBX"}).ok
    assert gen.validate("dna", {"sequence": "ATGC"}).ok
    assert not gen.validate("allele_freq", {"p": 1.5}).ok


# --- chemistry ---
def test_chemistry_molar_mass_and_gas():
    chem = get_plugin("chemistry")
    assert abs(chem.simulate("molar_mass", {"formula": "H2O"})["molar_mass_g_mol"] - 18.015) < 0.01
    v = chem.simulate("ideal_gas", {"n": 1.0, "T": 273.15, "P": 101325})["V"]
    assert abs(v - 0.022414) < 1e-4
    assert not chem.validate("formula", {"formula": "Xx2"}).ok


def test_unknown_simulator_raises():
    with pytest.raises(KeyError):
        get_plugin("physics").simulate("does_not_exist", {})


def test_unknown_domain_raises():
    with pytest.raises(KeyError):
        get_plugin("biology_wetlab")
