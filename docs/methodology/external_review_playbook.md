# External Review Playbook (human steps)

ACERO prepares review bundles and simulates review handling, but **external review
is a human process**. ACERO never contacts reviewers, never sends anything, and
never treats a review (or AI/model agreement) as validation. These are the steps a
human maintainer follows.

1. **Select a reviewer** — an independent domain expert with no conflict of
   interest, who did not build the pipeline.
2. **Verify experience** — confirm relevant expertise (here: transit photometry,
   time-series statistics, Kepler systematics).
3. **Share the bundle** — hand over the standalone package + review bundle
   manifest (version, commit, per-file SHA-256, AI disclosure, review questions).
   Sharing is a deliberate human act (see the publication-prohibition policy).
4. **Declare AI involvement** — provide `AI_DISCLOSURE.md`; an AI is not an author.
5. **Request critique** — ask the reviewer to reproduce, then to attack: red
   noise, multiple testing, detrending choices, false positives, the abstention.
6. **Import the review** — record it with `acero.reproduction`; run tamper
   detection (hashes, version, commit, optional signature). A favorable review is
   **recorded, not accepted**; verification is independent of the verdict.
7. **Respond** — address each point; corrections require human approval.
8. **Convert issues** — turn valid critiques into tracked issues / new experiments
   (e.g. "control red-noise false positives before any bounded claim").
9. **Update the version** — bump version + commit; rebuild the bundle so hashes
   bind to the new state.
10. **Decide the next step** — the human decides whether to seek further review,
    revise, or stop. ACERO never decides to publish.

## Guardrails

- No auto-acceptance: `ReviewLedger` sets `trusted = False` by construction.
- No false independence: two/three methods over the same data are not independent
  replication; a local re-run is `INDEPENDENT_PROCESS_REPRODUCTION` at most.
- No AI authorship; no AI/model consensus as evidence.
- No contact, no publication, no push, no merge — all human decisions.
