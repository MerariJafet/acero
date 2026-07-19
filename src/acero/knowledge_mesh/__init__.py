"""ACERO Scientific Knowledge Mesh (Phase 1).

A federated, auditable layer for DISCOVERING, VERIFYING, INDEXING and RETRIEVING
real scientific sources with full provenance. Non-negotiable principles:
  - Evidence before language: no factual claim is accepted just because an LLM said
    it. Every record ties to a real identifier (DOI/arXiv/PMID/accession/...).
  - Zero invented sources: every source is verified with a REAL request.
  - Epistemic separation: an ACERO/AI inference is NEVER stored as an observation.
  - Full traceability: source, identifiers, license, access, checksum, dates,
    verification and retraction status travel with every object.

Phase 1 scope: schema + verified source registry + a real Crossref connector.
Later phases add more connectors, hybrid search, a knowledge graph and
reproducibility (see docs/knowledge_mesh/IMPLEMENTATION_ROADMAP.md).
"""

from .models import (
    ObjectType,
    ProvenanceStep,
    ScientificObject,
    SourceRecord,
)

__all__ = ["ObjectType", "ScientificObject", "SourceRecord", "ProvenanceStep"]
