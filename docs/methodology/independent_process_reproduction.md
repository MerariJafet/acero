# Independent-Process Reproduction (methodology)

## What it is

Running a **standalone reproduction package** in a **separate local process** —
a fresh container, a fresh working directory, empty caches, and **no access to
the ACERO database, World Model, secrets, private prompts, or session** — and
checking that it produces the recorded outputs with matching data hashes.

## What it is NOT

It is **NOT external scientific replication**. External replication requires
independent *people*, independent *data*, and independent *instruments*. A
same-author, same-data local re-run — however isolated — cannot exceed:

```
MAX_STATE = INDEPENDENT_PROCESS_REPRODUCTION
```

ACERO encodes this ceiling (`acero.reproduction.independent`) so no local re-run
can be labelled external replication.

## The standalone package

`reproduction/transit_kepler8b/` depends only on `numpy`, `scipy`, `astropy`:

- `download_data.py` — fetches public Kepler light curves + records SHA-256.
- `analyze.py` — **three** methods: BLS, PDM, and a numpy-only matched-box
  (the alternative implementation; different code path, shared dep = numpy).
- `run_all.py` — download → analyze → compare to `expected_outputs.json`.
- `Dockerfile` — fully isolated container.
- README, LICENSE, CITATION.cff, requirements, preregistration, data manifests,
  expected outputs, negative results, review form, AI disclosure.

A static check (`package_is_standalone`) fails if any file imports `acero`.

## Evidence (this run)

Isolated Docker container, fresh cache, downloaded its own data:

```
reproduction_state: INDEPENDENT_PROCESS_REPRODUCTION
no_hash_drift:      true
method_A_BLS:        3.52326 d   (frac err 0.0002)
method_B_PDM:        3.52326 d   (frac err 0.0002)
method_C_matched:    3.52221 d   (frac err 0.00009)
is_discovery:        false
```

Full output: `docs/benchmarks/independent_process_reproduction_output.txt`.

## Drift, warnings, failures

Every reproduction records: outputs, per-file hashes, hash drift vs the manifest,
warnings, resource use, and any failure. A hash drift or a failed comparison marks
the reproduction as **not reproduced** — it is never silently ignored.
