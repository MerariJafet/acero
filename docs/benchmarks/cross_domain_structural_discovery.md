# Cross-Domain Structural Discovery Benchmark

Source: `benchmarks/cross_domain.py`. Validates the Cognitive Discovery Engine
end-to-end: identify shared structure, transfer a prediction, verify it, find where
the analogy fails, and update the World Model.

## Cases and results
| Pair | Status | Deep score | Outcome |
|---|---|---|---|
| mechanical oscillator ↔ RLC circuit | **STRUCTURALLY_SUPPORTED** | 0.95 | resonance ω₀=√(restoring/inertia) transferred and **verified in the sandbox** for both systems |
| thermal ↔ particle diffusion | **VALID_IN_REGIME** | 0.97 | same diffusion PDE; Fourier-number invariant; self-similar spreading √(D·t) |
| atom ↔ solar system | **MISLEADING** | 0.02 | geometric similarity, but quantised bound states ≠ classical orbits; refuted |

The recovered oscillator↔RLC mapping (mass↔inductance, damping↔resistance,
spring↔1/capacitance, displacement↔charge, velocity↔current, force↔voltage) is NOT
given to the engine — it is recovered from the shared 2nd-order-linear-ODE form and
matching term roles. First-principles corroboration recovers ω₀² ∝ k/m (one Pi
group).

## Integration
Each analogy updates a belief in the World Model: supported → Evidence + higher
confidence; misleading → CounterEvidence + preserved NegativeResult + lower
confidence.

## Honesty
- The analogies are KNOWN correspondences; this validates the METHOD, not a discovery.
- The resonance transfer is verified by simulation — a simulation proves nothing about
  the physical world.
- Dimensional analysis gives scaling, not the numeric constant.
- Deep scores are heuristic and uncalibrated.

## Run it
```bash
acero cognitive benchmark                 # full cross-domain benchmark
acero cognitive analogy atom_solar_system # one pair
acero cognitive dimensions period=time,length=length,gravity=acceleration,mass=mass
acero cognitive validate-equation force velocity
```
