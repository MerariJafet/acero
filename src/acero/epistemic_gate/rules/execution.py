"""Execution-stage gate rules (9.20)."""

from __future__ import annotations

from ..models import GateRule, Stage
from .common import rule

S = Stage.EXECUTION

RULES: list[GateRule] = [
    rule("ran_in_sandbox", S, "ran_in_sandbox", expect=True,
         detail="code ran outside the sandbox",
         remediation="execute experiment code in the restricted sandbox"),
    rule("no_secrets_exposed", S, "secrets_exposed", expect=False,
         detail="secrets were exposed to the executed code",
         remediation="run with a minimal environment; never pass os.environ"),
    rule("network_authorized", S, "unauthorized_network", expect=False,
         detail="unauthorized network access during execution",
         remediation="disable network or obtain explicit authorization"),
    rule("environment_recorded", S, "environment_recorded", expect=True,
         detail="execution environment was not recorded",
         remediation="record environment.json (python, platform, versions)"),
    rule("seeds_recorded", S, "seeds_recorded", expect=True,
         detail="random seeds were not recorded",
         remediation="record every RNG seed used"),
    rule("hashes_recorded", S, "hashes_recorded", expect=True,
         detail="input/code/output hashes were not recorded",
         remediation="record SHA-256 of inputs, code and outputs"),
    rule("timeout_configured", S, "timeout_configured", expect=True,
         detail="no execution timeout configured",
         remediation="configure a wall-clock timeout"),
    rule("code_versioned", S, "code_modified_unversioned", expect=False,
         detail="code was modified without a version record",
         remediation="version the exact script executed"),
    rule("reproducible", S, "reproduced", expect=True,
         detail="results did not reproduce on re-run",
         remediation="fix nondeterminism until the re-run matches"),
]
