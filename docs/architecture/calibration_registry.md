# Calibration Registry (Sprint 11)

Centralises `CalibrationObservation`s (predictor, type, probability/interval/class,
outcome, domain, benchmark, difficulty, version) across hypotheses, inferred terms,
governing models, analogies, derivations, gate warnings, the grader, abstention, and
discriminating experiments.

Metrics (computed only when n ≥ 8, else `INSUFFICIENT_CALIBRATION_DATA`): Brier, log loss,
ECE, MCE, reliability diagram, sharpness, interval coverage/width, risk-coverage curve,
selective accuracy, and abstention utility. Calibration is kept SEPARATE per
domain/task/difficulty/version — synthetic physics is never mixed with real astronomy or the
human grader. Recalibration (binning / temperature / interval inflation) fits on a
calibration split and refuses to touch the test split.
