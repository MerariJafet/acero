"""Canonical system representations for the cross-domain analogy benchmarks.

These are the STRUCTURAL descriptions ACERO compares. The oscillator↔RLC mapping is
NOT given to the analogy engine as an answer — the engine must recover it from the
shared structural form and matching term roles; this file is the benchmark truth set.
"""

from __future__ import annotations

from .models import SystemRepresentation

MECHANICAL_OSCILLATOR = SystemRepresentation(
    name="damped mechanical oscillator", domain="physics",
    variables={"displacement": "length", "velocity": "velocity", "mass": "mass",
               "damping": "mechanical_damping", "spring_constant": "spring_constant",
               "force": "force"},
    structural_form="2nd_order_linear_ode: a*y'' + b*y' + c*y = f",
    term_roles={"inertia": "mass", "dissipation": "damping", "restoring": "spring_constant",
                "response": "displacement", "flow": "velocity", "forcing": "force"},
    invariants=["total_energy_if_undamped"],
    symmetries=["time_translation"],
    dimensionless_groups={"damping_ratio": "b / (2*sqrt(a*c))",
                          "resonance": "sqrt(c/a)"})

RLC_CIRCUIT = SystemRepresentation(
    name="series RLC circuit", domain="physics",
    variables={"charge": "charge", "current": "current", "inductance": "inductance",
               "resistance": "resistance", "inverse_capacitance": "inverse_capacitance",
               "voltage": "voltage"},
    structural_form="2nd_order_linear_ode: a*y'' + b*y' + c*y = f",
    term_roles={"inertia": "inductance", "dissipation": "resistance",
                "restoring": "inverse_capacitance", "response": "charge",
                "flow": "current", "forcing": "voltage"},
    invariants=["total_energy_if_undamped"],
    symmetries=["time_translation"],
    dimensionless_groups={"damping_ratio": "b / (2*sqrt(a*c))",
                          "resonance": "sqrt(c/a)"})

THERMAL_DIFFUSION = SystemRepresentation(
    name="thermal diffusion", domain="physics",
    variables={"temperature": "temperature", "thermal_diffusivity": "diffusivity",
               "position": "length", "time": "time"},
    structural_form="diffusion_pde: dphi/dt = D * d2phi/dx2",
    term_roles={"field": "temperature", "diffusivity": "thermal_diffusivity",
                "space": "position", "time": "time"},
    invariants=["total_heat_conserved_no_source"],
    symmetries=["space_translation", "time_translation"],
    dimensionless_groups={"fourier_number": "D*time/length**2"})

PARTICLE_DIFFUSION = SystemRepresentation(
    name="particle (mass) diffusion", domain="chemistry",
    variables={"concentration": "amount", "mass_diffusivity": "diffusivity",
               "position": "length", "time": "time"},
    structural_form="diffusion_pde: dphi/dt = D * d2phi/dx2",
    term_roles={"field": "concentration", "diffusivity": "mass_diffusivity",
                "space": "position", "time": "time"},
    invariants=["total_mass_conserved_no_source"],
    symmetries=["space_translation", "time_translation"],
    dimensionless_groups={"fourier_number": "D*time/length**2"})

# Negative case: the atom is NOT structurally a tiny solar system.
ATOM = SystemRepresentation(
    name="atom (quantum)", domain="physics",
    variables={"electron": "dimensionless", "nucleus": "mass", "energy_level": "energy",
               "quantum_number": "dimensionless"},
    structural_form="quantized_bound_state: discrete energy levels, no classical orbit",
    term_roles={"center": "nucleus", "bound_particle": "electron"},
    invariants=["quantized_angular_momentum", "energy_levels_discrete"],
    symmetries=["rotation"],
    dimensionless_groups={"fine_structure": "alpha"})

SOLAR_SYSTEM = SystemRepresentation(
    name="solar system (classical)", domain="astronomy",
    variables={"planet": "mass", "star": "mass", "orbit_radius": "length",
               "period": "time"},
    structural_form="classical_kepler_orbit: continuous orbits, 1/r^2 force",
    term_roles={"center": "star", "orbiting_body": "planet"},
    invariants=["angular_momentum_continuous", "energy_continuous"],
    symmetries=["rotation", "time_translation"],
    dimensionless_groups={"eccentricity": "e"})

BENCHMARK_PAIRS = {
    "oscillator_rlc": (MECHANICAL_OSCILLATOR, RLC_CIRCUIT),
    "thermal_particle_diffusion": (THERMAL_DIFFUSION, PARTICLE_DIFFUSION),
    "atom_solar_system": (ATOM, SOLAR_SYSTEM),
}
