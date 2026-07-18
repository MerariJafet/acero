# Standalone Reproduction — Kepler-8b Transit Recovery

This package reproduces the **transit-recovery** result of ACERO's Sprint-24
program **without any access to ACERO**: no ACERO database, no World Model, no
secrets, no internal caches, no private prompts, no ACERO session. It depends only
on `numpy`, `scipy`, and `astropy` and downloads its own public data.

**It makes no discovery claim.** Recovering the *known* transit of Kepler-8b is
recovery, not discovery. Injected signals are tests, not observations. Reproducing
this package in another local process is **INDEPENDENT_PROCESS_REPRODUCTION** —
NOT external scientific replication (which requires independent people, data, and
instruments).

## Contents

```
README.md              this file
LICENSE                license for this reproduction package
CITATION.cff           how to cite (machine-readable)
requirements.txt       exact runtime dependencies
Dockerfile             fully isolated container
download_data.py       downloads public Kepler LCs + records SHA-256
analyze.py             two pipelines (BLS + PDM) + a THIRD alternative method
run_all.py             download -> analyze -> compare to expected outputs
preregistration.json   the plan, hashed before analysis (copied from the program)
data_manifests.json    provenance for every file (URL, license, hash, size)
expected_outputs.json  expected recovered period + tolerance
negative_results.md    preserved negatives (why the program abstains)
review_form.md         a human reviewer's structured form
AI_DISCLOSURE.md       AI involvement disclosure
```

## Run (no ACERO)

```bash
pip install -r requirements.txt
python run_all.py
```

or fully isolated:

```bash
docker build -t kepler8b-repro .
docker run --rm kepler8b-repro
```

Expected: both pipelines and the alternative method recover P ≈ 3.5225 d
(frac error < 0.005), and the file hashes match `data_manifests.json`.
