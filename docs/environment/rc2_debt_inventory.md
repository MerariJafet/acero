# RC2 Technical Debt Inventory (Fase 0, Programa 2.1)

| Item | Finding | Class | Planned |
|---|---|---|---|
| TODO/FIXME | none real (only Spanish "no descubre nada" honesty notes) | ok | — |
| NotImplementedError | domains/core abstract methods; discovery/search documented FUTURE strategies (bayesian/evolutionary/active) that raise with a message; llm provider abstract | documented stubs (not production mocks) | keep |
| bare `pass` | 8 (dataclass bodies / protocol stubs) | ok | — |
| production mocks | MockProvider is the deterministic default LLM (by design); no result-hardcoding | ok | — |
| migrations | `create_all` idempotent + lightweight schema_version (v3); no Alembic | DEBT | **Sprint 22** |
| API/portal auth | no authentication (local-first, read-only + gated writes) | DEBT | **Sprint 23** (local auth) |
| in-memory runtime | worker drains synchronously; tokens per-process | DEBT | **Sprint 22** (multiprocess) |
| frontend testing | portal tested via pytest (route/DOM/security), no browser E2E | DEBT | **Sprint 23** (Playwright) |
| vestigial packages | hypothesis/contracts (unused), integrations/, knowledge/ (empty) | documented | keep (provenance) |
| second science program | only SILSO sunspots | DEBT | **Sprint 24** (exoplanet transit) |
| independent replication | own reproduction only | DEBT | **Sprint 25** |

No dead adapters or duplicate modules of concern. `create_all` appears in 10 places (all the
canonical schema bootstrap + tests).
