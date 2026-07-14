# Gate Bypass Benchmark

Source: `benchmarks/gate_bypass.py`. Seven attempts to slip a defective mutation past the
inline gate — ALL blocked (`True` = blocked):

1. direct World-Model write (no gate) → `BypassDetected`
2. accept evidence without provenance → `GateBlockedError`
3. close a non-reproducible run → BLOCKED
4. promote a surface-only analogy → BLOCKED
5. resolve a misconception without new evidence → refused
6. export a genetic association as causal → BLOCKED
7. accept a chemistry prediction violating mass balance → BLOCKED

```bash
acero gate bypass-test
```
