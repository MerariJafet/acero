"""Mutation tokens (Sprint 11).

A protected scientific mutation requires a token minted only after a valid gate PASS. A
token is: specific to one action, limited to named artifacts, short-lived, single-use,
non-transferable across projects/actions, and replay-proof. The token itself never permits
a NEW mutation — it only authorises the exact one it was minted for.

Tokens are HMAC-signed over their fields with a per-process secret so a tampered token
fails verification; verification also checks a single-use ledger so a replay is rejected.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ..core.clock import now
from ..core.ids import new_id

# Per-process secret. Not persisted: tokens do not survive a restart (by design — a token
# is short-lived and single-use within one run).
_SECRET = os.urandom(32)


class TokenError(Exception):
    """Raised when a mutation token is invalid, expired, replayed, or mismatched."""


@dataclass
class MutationToken:
    token_id: str
    action: str
    project_id: str
    artifact_ids: tuple[str, ...]
    rule_versions: tuple[str, ...]
    issued_at: str
    expires_at: str
    signature: str = ""

    def _payload(self) -> bytes:
        return "|".join([
            self.token_id, self.action, self.project_id,
            ",".join(sorted(self.artifact_ids)), ",".join(sorted(self.rule_versions)),
            self.issued_at, self.expires_at]).encode()

    def sign(self) -> None:
        self.signature = hmac.new(_SECRET, self._payload(), hashlib.sha256).hexdigest()

    def verify_signature(self) -> bool:
        expected = hmac.new(_SECRET, self._payload(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    def as_dict(self, *, redact: bool = True) -> dict[str, Any]:
        d = {"token_id": self.token_id, "action": self.action,
             "project_id": self.project_id, "artifact_ids": list(self.artifact_ids),
             "rule_versions": list(self.rule_versions), "issued_at": self.issued_at,
             "expires_at": self.expires_at}
        if not redact:
            d["signature"] = self.signature
        return d


@dataclass
class TokenRegistry:
    """Mints and validates single-use tokens; tracks spent tokens (replay protection)."""

    ttl_seconds: int = 30
    _spent: set[str] = field(default_factory=set)
    _revoked: set[str] = field(default_factory=set)
    issued: int = 0
    spent: int = 0
    replays_blocked: int = 0
    expired_blocked: int = 0

    def issue(self, *, action: str, project_id: str,
              artifact_ids: tuple[str, ...] = (),
              rule_versions: tuple[str, ...] = ()) -> MutationToken:
        tok = MutationToken(
            token_id=new_id("mtok"), action=action, project_id=project_id,
            artifact_ids=tuple(artifact_ids), rule_versions=tuple(rule_versions),
            issued_at=now().isoformat(),
            expires_at=(now() + timedelta(seconds=self.ttl_seconds)).isoformat())
        tok.sign()
        self.issued += 1
        return tok

    def validate(self, tok: MutationToken, *, action: str, project_id: str,
                 artifact_ids: tuple[str, ...] = ()) -> None:
        """Raise TokenError unless the token is valid for exactly this action/project/
        artifacts, unexpired, unspent, unrevoked, and untampered."""
        if not tok.verify_signature():
            raise TokenError("token signature invalid (tampered)")
        if tok.token_id in self._revoked:
            raise TokenError("token revoked")
        if tok.token_id in self._spent:
            self.replays_blocked += 1
            raise TokenError("token already used (replay)")
        try:
            exp = datetime.fromisoformat(tok.expires_at)
        except ValueError as e:
            raise TokenError("token expiry unparseable") from e
        if now() > exp:
            self.expired_blocked += 1
            raise TokenError("token expired")
        if tok.action != action:
            raise TokenError(f"token action mismatch ({tok.action} != {action})")
        if tok.project_id != project_id:
            raise TokenError("token project mismatch")
        if artifact_ids and set(artifact_ids) - set(tok.artifact_ids):
            raise TokenError("token does not authorise these artifacts")

    def spend(self, tok: MutationToken) -> None:
        """Mark a token used. A second spend (replay) will fail validation."""
        self._spent.add(tok.token_id)
        self.spent += 1

    def revoke(self, token_id: str) -> None:
        self._revoked.add(token_id)

    def metrics(self) -> dict[str, int]:
        return {"issued": self.issued, "spent": self.spent,
                "replays_blocked": self.replays_blocked,
                "expired_blocked": self.expired_blocked,
                "revoked": len(self._revoked)}
