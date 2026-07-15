# Methodology — Scientific Calibration

Confidence must match observed accuracy. ACERO measures Brier / log loss / ECE / MCE /
coverage / sharpness / risk-coverage / abstention utility, per domain / task / difficulty /
version, and refuses to report a metric below n = 8 (`INSUFFICIENT_CALIBRATION_DATA`).
Recalibration is fit on a calibration split, never on the evaluation split; overlapping
splits raise a leakage error. An uncalibrated confidence is never presented as a probability.
