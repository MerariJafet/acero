# Write Surface Inventory (Sprint 11)

Every path that can create / update / delete / promote / invalidate / accept / close /
export / modify confidence or an epistemic state. Classification:
`PROTECTED` (goes through the inline gate / a mutation token), `READ_ONLY`,
`LEGACY_UNPROTECTED` (must be closed before Sprint 11 ends), `ADMIN_ONLY`, `DEPRECATED`.

| Store / surface | Method | Kind | Class | Notes |
|---|---|---|---|---|
| World Model | `update_belief` | modify confidence | **PROTECTED** | `require_context` + guarded via `GatedWorldModel` (Sprint 10) |
| World Model | `link` | accept relation | **PROTECTED** | `require_context` |
| World Model | `reweight_edge` | weaken/invalidate | **PROTECTED** | guarded in Sprint 11 |
| World Model | `add_node` | create | **PROTECTED** | guarded in Sprint 11 (accepted-node create) |
| World Model | `update_node_data` | update | **PROTECTED** | guarded in Sprint 11 |
| Discovery Store | `put` | create/update | **PROTECTED** | guarded via `GuardedDiscoveryStore` |
| Discovery Store | `set_status` | promote/close | **PROTECTED** | guarded |
| Discovery Store | `update_payload` | update | **PROTECTED** | guarded |
| Discovery Store | `delete` | delete | **PROTECTED** | already blocks negatives/rejected; now gated |
| Negative Registry | `record` | create | **PROTECTED** | preserved-negatives invariant + gate |
| Understanding Store | `save_*` | grant level / resolve | **PROTECTED** | comprehension mutations gated |
| Ledger | `add_entity` | create | **ADMIN_ONLY** | provenance backbone; used by boundary services |
| Ledger | `update_entity` | update | **ADMIN_ONLY** | anti-HARKing guard already present |
| Ledger | `delete_entity` | delete | **ADMIN_ONLY** | blocks NEGATIVE_RESULT |
| Ledger | `record_event` | append provenance | **READ_ONLY-append** | append-only audit log; never mutated |
| Literature Store | ingest/associate citation | create | **PROTECTED** | LITERATURE-stage gate |
| Domain Labs | benchmarks / simulate | compute | **READ_ONLY** | pure computation, no persistence |
| Tool Registry | register/quarantine | create/update | **PROTECTED** | screen→sandbox→quarantine (Sprint 7) + gate |
| Publication Candidate | prepare | create/update | **PROTECTED** | never auto-publishes; readiness-gated (Sprint 11) |
| API writes | POST /projects | create | **PROTECTED** | boundary; no arbitrary mutation exposed |
| CLI writes | project/discovery/world | create/update | **PROTECTED** | go through boundary services |
| Migrations / admin scripts | schema | admin | **ADMIN_ONLY** | run by a human; not a scientific mutation |

## Enforcement mechanism (Sprint 11)
Scientific mutations go through `epistemic_gate.enforcement.enforce()` which now issues a
short-lived, single-use **mutation token** after a PASS. Guarded persistence
(`epistemic_gate/integration/`) requires an active `GateExecutionContext` (contextvars,
async/worker/subprocess-safe) AND a valid token for the specific action + artifacts. A
`UnitOfWork` coordinates multi-store mutations with rollback.

## Status
No central scientific write path remains `LEGACY_UNPROTECTED`: World Model, Discovery,
Understanding, Negative Registry, Literature and Publication candidates are `PROTECTED`;
the ledger/provenance backbone is `ADMIN_ONLY` (append-only log) used by boundary services.
An architectural import test (`tests/unit/test_write_surface.py`) fails if a non-boundary
module imports a persistence class directly.
