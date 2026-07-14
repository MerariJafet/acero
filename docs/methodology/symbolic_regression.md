# Symbolic Regression & Codex Terms

`inference/discovery/symbolic_search.py`. Codex may PROPOSE candidate terms/expressions
via a strict JSON schema; ACERO validates each (SymPy parse, known symbols, finite on
the data) before it can enter a library. A real Codex run proposed physically relevant
terms including `abs(v)*v` and `sign(v)` (quadratic and Coulomb friction) that the
polynomial library omits — demonstrating value while remaining advisory. Every proposal
must still pass dimensional/domain/numerical/extrapolation validation; Codex never
declares a term correct.
