# Sprint 25 — Independent Replication & External Review Protocol

Date: 2026-07-18
Branch: `integration/acero-2.1-program`
Status: **complete** · `make verify` green

## Objective

Build a package that a clean, separate process can reproduce **without any ACERO
internal state**, and prepare (but never perform) external human review.

## 25.1 Standalone reproduction package

`reproduction/transit_kepler8b/` — depends only on numpy/scipy/astropy; imports
**no** ACERO. Ships: README, LICENSE, CITATION.cff, requirements, Dockerfile,
`download_data.py`, `analyze.py`, `run_all.py`, preregistration, data manifests,
expected outputs, negative results, review form, AI disclosure. A static check
(`package_is_standalone`) fails if any file imports `acero`.

## 25.2 Independent-process reproduction (evidence)

Built and ran the package in a **fully isolated Docker container** (fresh
OS/Python/cache; no ACERO DB, World Model, secrets, or caches). It downloaded its
own data (**hashes match the manifest, no drift**) and recovered the known period:

```
state:            INDEPENDENT_PROCESS_REPRODUCTION   (NOT external replication)
method_A_BLS:     3.52326 d  (frac err 0.0002)
method_B_PDM:     3.52326 d  (frac err 0.0002)
method_C_matched: 3.52221 d  (frac err 0.00009)
no_hash_drift:    true      | is_discovery: false
```

Evidence: `docs/benchmarks/independent_process_reproduction_output.txt`. The
ceiling is encoded in `acero.reproduction.independent` (`MAX_STATE`), so no local
re-run can be mislabelled as external replication.

## 25.3 Alternative implementation

`method_C_matched_box` is a **numpy-only** box matched-filter — a different method
and code path from the BLS/PDM pipelines, answering the same question on the same
data. Shared dependency (numpy) is recorded. All three agree on the period.

## 25.4–25.5 Review bundle + security

`acero.reproduction.bundle`: builds a manifest binding files → SHA-256 + version +
commit + AI disclosure + review questions, with an optional HMAC signature.
`verify_bundle` performs **tamper detection**: detects modified files, missing
files, version/commit drift, and bad/absent signatures. Nothing is trusted on its
word.

## 25.6 External review simulation

`acero.reproduction.simulation`: the ten required fixtures (correct, superficial
favorable, valid critique, wrong critique, tampered, wrong version, unsigned,
conflict of interest, failed reproduction, missing evidence). The `ReviewLedger`
**records** every review with `trusted = False` by construction — auto-acceptance
is impossible; verification status is independent of the reviewer's verdict.

## 25.7 External review playbook

`docs/methodology/external_review_playbook.md` — ten human steps (select reviewer
→ verify experience → share bundle → declare AI → request critique → import review
→ respond → convert issues → update version → decide). ACERO never contacts,
sends, or publishes.

## Tests (8 new)

`tests/unit/test_reproduction.py`: standalone-no-ACERO-imports, required files,
bundle build/verify, modification/missing/version/commit detection, signature
roundtrip + tamper, review simulation never-auto-trusts, independent-state never
external replication.

## Honesty

INDEPENDENT_PROCESS_REPRODUCTION is not external replication. Three methods over
the same data are not independent replication. A favorable review is not
validation. No contact, no publication, no push, no merge.

Docs: `docs/methodology/independent_process_reproduction.md`,
`docs/methodology/external_review_playbook.md`.

Commit: `sprint-25: independent-process reproduction and review protocol`
