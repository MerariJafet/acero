# ACERO Scientific Knowledge Mesh — Implementation Roadmap

Goal: give ACERO **verifiable access to the raw material of science** — discover,
verify, index and retrieve real sources with full provenance — so the copilot can
ground hypotheses in real evidence, never invented sources.

## Phased plan (honest: this is a multi-session build)

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Audit current repo (data.py MAST download, exoplanet CSV, world-model graph, provenance) | **done** |
| 1 | Schema (`ScientificObject`, epistemic types) + verified Source Registry (9 sources, real health checks) + **Crossref connector** (metadata, license, retraction detection) + CLI + portal search + tests | **done (this session)** |
| 2 | Connectors: OpenAlex, arXiv, NCBI E-utils, PubChem, Zenodo, GWOSC, NASA MAST — each with health_check/search/fetch_metadata/normalize/checksum | pending |
| 3 | Identity resolver + deduplication (DOI↔arXiv↔PMID↔accession; versions) | pending |
| 4 | Scientific integrity pipeline (retractions/corrections/EoC at scale; cross-source verification ≥2 independent systems) | partial (Crossref retraction detection works) |
| 5 | Hybrid retrieval: lexical + semantic (pgvector) + identifier + structured + knowledge graph | pending |
| 6 | Evidence-first Retrieval Gateway (query plan → sources → results w/ provenance, contradictions, limitations) | partial (Crossref search) |
| 7 | On-demand file/dataset download (Level C/D) with checksums, license gate, dedup, resumable | pending |
| 8 | Reproducibility agent (locate data+code, rerun controlled cases) | pending |
| 9 | Adversarial reviewer (fake sources, dead DOIs, prompt-injection in documents, retracted-as-evidence) | pending |
| 10 | Storage plan (PostgreSQL + pgvector + object store + content-addressed) — introduced only when proven necessary | pending |

## Download strategy (never download everything)
- **Level A** source registry · **Level B** metadata index (default) · **Level C**
  full text/dataset on demand · **Level D** strategic collections via official bulk
  (with size/cost/license shown first). No paid services, no restricted data, no
  auth evasion, respect rate limits + robots + ToS.

## Security (enforced from Phase 2)
Secrets only via env; parsers sandboxed; size/zip-bomb/path-traversal/MIME guards;
**documents are data, not instructions** (prompt-injection in papers is neutralized).

## Acceptance (Phase-1 slice met; full target is the prompt's 95% rubric)
Phase 1 delivered: ≥8 verified sources across ≥5 domains, all with health checks,
1 tested connector, provenance on every object, retraction detection, licenses
recorded, tests green, no invented sources, no unauthorized cost. The full ≥25
sources / ≥10 connectors / hybrid-search / reproducibility target remains a
multi-phase build and is **not** claimed done.

## Deliverables produced (Phase 1)
`SCIENTIFIC_SOURCE_REGISTRY.md`, `scientific_source_registry.{json,csv}`, this
roadmap, the `acero.knowledge_mesh` package (models/sources/connectors/mesh),
CLI `acero mesh`, portal `/api/mesh/search`, tests. Remaining mandated docs
(PROVENANCE_MODEL, LICENSE_AND_ACCESS_MATRIX, SECURITY_THREAT_MODEL, etc.) are
scheduled for the phases that implement their subsystems — not written ahead of
real code.
