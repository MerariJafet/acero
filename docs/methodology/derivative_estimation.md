# Derivative Estimation

No single strategy fits all data. `inference/data/derivatives.py` offers finite
differences (central + one-sided edges), Savitzky–Golay smoothing (robust to noise),
and smoothing splines, with graceful fallback when SciPy or the window is unsuitable.
Each result records the method, parameters, an estimated error, and the UNRELIABLE
indices (temporal edges and large sampling gaps). `estimate(method='auto')` picks
Savitzky–Golay when the series looks noisy, else finite differences. Caveat: in SINDy,
derivatives are estimated from the SAME data used for regression — a high R² can be
interpolation, not identification (disclosed in every report).
