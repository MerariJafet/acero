# Physics Lab

**Scope:** classical mechanics, dynamical systems, oscillations, diffusion, waves, basic
thermodynamics/EM, intro computational QM, complex systems. NOT high-energy physics or 3-D
turbulent PDE. Safety: LOW.

**Term library** (dimension-aware): linear / quadratic / Coulomb friction, saturation,
periodic forcing, gradient, laplacian. **Solvers** (auditable, with method/step/stability/
error): RK4, symplectic/explicit Euler, FTCS diffusion (CFL r≤0.5), leapfrog wave
(Courant≤1).

**Benchmark (8):** nonlinear-friction oscillator, large-angle pendulum (longer period),
1-D diffusion (variance grows), 1-D wave (bounded), reaction–diffusion, conservation drift
(<2%), forced resonance (peak at ω₀), and an unstable explicit-Euler run whose instability
is DETECTED so the gate rejects the false evidence.

**Gate rules:** units_consistent, solver_stable, simulation_not_physical_validation.

**Limitations:** 1-D PDE, explicit schemes, small-parameter regimes; a simulation is not a
physical measurement.
