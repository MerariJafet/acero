# Calibration

`inference/calibration/calibration.py`. Confidence scores are calibrated EMPIRICALLY
against known-truth benchmarks: reliability diagram, Brier score, log loss, interval
coverage, and bootstrap confidence intervals. Calibration must not be measured only on
the system used to develop the scores. ACERO explicitly distinguishes a heuristic score,
an empirical frequency, a posterior model probability, an uncertainty interval, and LLM
confidence — these are NEVER mixed, and LLM confidence is never treated as a scientific
probability. Undeclared known miscalibration is a gate blocker.
