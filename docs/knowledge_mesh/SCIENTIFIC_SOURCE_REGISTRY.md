# Scientific Source Registry — Phase 1 (verified)

Part of the **ACERO Scientific Knowledge Mesh**. Every source below was verified
with a **real HTTP request** — none are invented. Machine-readable:
`scientific_source_registry.json` / `.csv`.

## Verified seed sources (9)

| source_id | institution | authority | domains | health | metadata license |
|-----------|-------------|-----------|---------|--------|------------------|
| crossref | Crossref | official_aggregator | all | active (200) | CC0 metadata |
| openalex | OurResearch | official_aggregator | all | active (200) | CC0 |
| arxiv | Cornell/arXiv | primary | physics, astro, math, cs, quant-ph | active (200) | arXiv terms |
| nasa_mast | STScI / NASA | primary | astronomy | active (200) | public domain |
| gwosc | LIGO/Virgo/KAGRA | primary | gravitational waves | active (200) | open |
| ncbi_eutils | NCBI / NIH | primary | genetics, genomics, biology | active (200) | US Gov PD (most) |
| pubchem | NCBI / NIH | primary | chemistry | active (200) | public domain (most) |
| zenodo | CERN / OpenAIRE | official_aggregator | all | active (200) | metadata CC0; **files vary** |
| datacite | DataCite | official_aggregator | all | active (200) | CC0 |

Domains covered: **literature/metadata, astronomy, gravitational waves, genomics,
chemistry, general repositories** (≥5 scientific domains). Verify live:
`acero mesh health`.

## Non-negotiable principles enforced
- **Zero invented sources** — a source not verified by a real request is not listed
  (or is marked, e.g. an earlier DataCite probe URL timed out; the `/heartbeat`
  endpoint later verified active).
- **Epistemic separation** — `ScientificObject.object_type` includes `ACERO_INFERENCE`
  / `ACERO_HYPOTHESIS`; `is_acero_generated` prevents treating AI output as observed data.
- **Licenses recorded** — metadata vs file license kept separate (esp. Zenodo).
- **Personal-data risk flagged** — NCBI marked `personal_data_risk: high`;
  controlled-access human data must NOT be ingested without authorization.

## What works today (Phase 1)
- `acero mesh sources|health|lookup <doi>|search <query>` (CLI).
- Portal: `/portal/api/mesh/search` + a "Buscar literatura científica REAL" box per project.
- **Crossref connector**: real DOI metadata + license + **retraction/correction
  detection** (reverse Crossref lookup — verified on the retracted Wakefield 1998 paper).

## Honest limitations (Phase 1)
- Only the Crossref connector is `tested`; the other 8 are registered/prototype
  (health-checked, not yet full connectors).
- No semantic/vector search, no knowledge graph, no bulk ingestion yet — see the
  roadmap.
