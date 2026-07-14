# Multi-Domain Scientific Reasoning Benchmark

Source: `benchmarks/multi_domain.py`. Four tracks + cross-domain transfer, each ending at
the Global Epistemic Gate.

| Track | ACERO does | Gate |
|---|---|---|
| Physics | select terms, integrate, check stability & conservation, infer limits | rejects false evidence from an unstable solver |
| Astronomy | clean, keep gaps, detect periodicity, check alias, ABSTAIN on mechanism | blocks a causal claim from an association |
| Genetics | detect spurious association, correct for structure & multiple testing, avoid causality | blocks a false causal inference |
| Chemistry | identify the form, check units & mass, infer parameters, detect non-identifiability | blocks a stoichiometry violation |
| Transfer | recognise shared saturation structure across chemistry↔genetics | shared structure, NOT identity |

All four tracks pass 8/8 and the gate blocks each flawed result.

```bash
acero benchmark multi-domain
```
