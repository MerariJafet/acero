# Active Experimentation (Sprint 8.9)

Source: `inference/active_experiments/`. When models are observationally equivalent on
the current data, ACERO designs the next measurement that would distinguish them
instead of picking whichever fits best.

`design(model_a, model_b, variables, candidate_ics, ...)` integrates both candidate
ODEs from each candidate initial condition and picks the IC/region of MAXIMUM
trajectory divergence, returning a `DiscriminatingExperiment` (proposed intervention,
IC, variables to measure, sampling rate, predicted divergence, expected information
gain, cost, risk, assumptions, failure modes). The DESIGN simulates known polynomial
ODEs in-process; real experiment EXECUTION runs through the sandbox. The active loop
integrates with the Discovery Engine scheduler and research utility.

Tests: `tests/unit/test_inference_active_calibration.py`.
