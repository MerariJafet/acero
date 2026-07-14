# Knowledge Transfer Benchmark

Source: `assessment/transfer.py` + benchmark case "transfer". Real mastery requires using a
concept in a DIFFERENT domain than it was learned in, WITHOUT being shown the mapping.

Transfer tasks (the mapping is deliberately withheld):
- **identifiability**: harmonic oscillator → logistic growth (can you identify K when the
  data never approaches carrying capacity? — no).
- **diffusion**: thermal → population (what plays the role of temperature? where does the
  analogy break?).
- **overfitting**: curve fitting → a new classifier (why is 100% training accuracy not good
  news?).
- **dimensional analysis**: pendulum → a new fluid problem (scale drag with velocity/density
  by units; state what dimensional analysis cannot give).

Passing a transfer task is the ONLY evidence that yields TRANSFER_CAPABLE / MASTERED. A
wrong transfer answer (e.g. "K is uniquely determined by the fit") scores 0 and is flagged
via the rubric's forbidden elements.
