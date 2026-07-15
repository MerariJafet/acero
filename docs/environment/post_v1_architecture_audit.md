# Post-v1 Architecture Audit (Fase 0)

## Size
- **253** Python source files, **~22,463** LOC in `src/acero/`.
- **69** test files, **~5,885** LOC; **586** tests passing; ruff + mypy clean.
- **25** top-level packages under `src/acero/`.

## Packages (all with real use + tests unless noted)
core, policies, epistemology, provenance, ledger, literature, evaluation, sandbox,
experiment, pedagogy, llm, cli, api, domains, discovery, world_model, cognitive, inference,
understanding, epistemic_gate, reliability, publication, benchmarks.

## Vestigial / placeholder (documented, retained for provenance — NOT deleted)
- `hypothesis/contracts.py` — Sprint 1–4 agent Protocols; superseded by `discovery/` and the
  orchestrator; currently imported nowhere. Harmless interface documentation of intent.
- `integrations/` — empty namespace (`__init__.py` only). Reserved for future external
  adapters; no code, no imports.
- `knowledge/` — empty namespace (`__init__.py` only). Reserved; no code, no imports.

Decision: retain (deleting risks erasing provenance and is low-value); flagged here so they
are not mistaken for live functionality. `acero doctor --deep` reports them.

## Persistence
- Single SQLite DB by default (`ledger/db.py`), tables in `ledger/models.py`: projects,
  entities, entity_history, runs, provenance, decisions, documents, fragments, world_nodes,
  world_node_history, world_edges, discovery. The generic `discovery` table backs Discovery,
  Understanding, and (Sprint 12) publication persistence via `DiscoveryStore`.
- No Alembic yet — `init_db` does `create_all` (idempotent). Schema versioning is a Sprint-13
  item (added: `schema_version` table + `acero doctor --deep` check).

## "Mock" usage (NOT production mocks that hide logic)
`llm/providers.py` MockProvider is the deterministic default LLM provider (by design; paid
providers gated). `discovery/generation.py` and `cognitive/analogies/candidates.py` reference
it only as the default; real Codex is opt-in via `ACERO_LLM_PROVIDER=codex`.

## Debt / follow-ups
- Runtime persistence for tokens/leases/contexts is in-process (Sprint 14 target).
- Portal/frontend not yet built (Sprint 15).
- No hardcoded scientific results found; benchmarks compute real values; datasets gated.
