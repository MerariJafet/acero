# Sparse Identification (STLSQ)

`inference/discovery/sparse_identification.py`. A SINDy-inspired sequential thresholded
RIDGE regression: fit dX/dt against the library Θ(X) on normalised columns, zero
coefficients below a threshold, refit, iterate. Ridge (Tikhonov) regularisation
suppresses the null-space blow-up from collinear terms (e.g. when a conserved quantity
makes {1, x², v²} linearly dependent), so thresholding can remove them. We report
STABILITY selection (fraction of threshold×bootstrap runs selecting each term) and
threshold sensitivity — never a single point estimate. This is SYSTEM IDENTIFICATION
from an IMPOSED library, not "discovering a law".
