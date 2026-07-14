# Invariant Discovery

`inference/discovery/invariants.py`. Conserved quantities are the LOW-VARIANCE
directions of the centred feature covariance: the eigenvector with smallest eigenvalue
gives the most-conserved combination. The trivial constant term is excluded. Candidates
are classified exact (<1% relative variation) / approximate (<10%) / dataset-specific /
artifact, and verified under noise (an invariant should survive moderate noise). For the
harmonic oscillator the recovered invariant involves x² and v² — the conserved energy.
