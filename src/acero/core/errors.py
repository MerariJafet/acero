"""ACERO error hierarchy. Failures are explicit, never silently swallowed."""

from __future__ import annotations


class AceroError(Exception):
    """Base class for all ACERO errors."""


class ConfigError(AceroError):
    """Invalid or missing configuration."""


class PolicyViolation(AceroError):
    """An action was blocked by policy (cost, safety, autonomy, execution)."""


class IntegrityError(AceroError):
    """A scientific-integrity invariant was violated (orphan result, missing prereg, etc.)."""


class ProvenanceError(AceroError):
    """A claim/evidence lacks required provenance."""


class SandboxError(AceroError):
    """Sandboxed execution failed, timed out, or was refused by static screening."""


class RetrievalError(AceroError):
    """Literature ingestion or retrieval failure."""


class WorkflowError(AceroError):
    """Illegal research-workflow state transition."""
