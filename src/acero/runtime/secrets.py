"""Local HMAC secret management (Sprint 14).

The mutation-token secret comes from the environment (``ACERO_HMAC_SECRET``, hex/base) with a
key id (``ACERO_HMAC_KEY_ID``). In *development* mode an ephemeral per-process secret is
generated and clearly labelled. In *production* mode (``ACERO_ENV=production``) startup that
needs signing REFUSES without a configured secret. The secret is never stored in Git and
never printed in full.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

_ENV_SECRET = "ACERO_HMAC_SECRET"
_ENV_KEY_ID = "ACERO_HMAC_KEY_ID"

# ephemeral dev secret, generated once per process (labelled, never persisted)
_DEV_SECRET = os.urandom(32)
_DEV_KEY_ID = "dev-" + hashlib.sha256(_DEV_SECRET).hexdigest()[:8]


class InsecureStartupError(RuntimeError):
    """Raised when production mode needs a secret but none is configured."""


@dataclass
class SecretInfo:
    mode: str            # development | production
    key_id: str
    configured: bool     # True if an env-provided secret is present


def _is_production() -> bool:
    return os.environ.get("ACERO_ENV", "development").lower() == "production"


def get_secret(*, require: bool = False) -> tuple[str, bytes]:
    """Return (key_id, secret_bytes). In production a configured secret is mandatory."""
    raw = os.environ.get(_ENV_SECRET)
    if raw:
        key_id = os.environ.get(_ENV_KEY_ID, "env-" + hashlib.sha256(raw.encode()).hexdigest()[:8])
        return key_id, hashlib.sha256(raw.encode()).digest()
    if _is_production() or require:
        raise InsecureStartupError(
            f"{_ENV_SECRET} is not set; refusing to sign in production. "
            "Run 'acero secrets init' and export the printed value.")
    return _DEV_KEY_ID, _DEV_SECRET


def secret_status() -> dict[str, object]:
    info = _status()
    return {"mode": info.mode, "key_id": info.key_id, "configured": info.configured}


def _status() -> SecretInfo:
    configured = bool(os.environ.get(_ENV_SECRET))
    mode = "production" if _is_production() else "development"
    if configured:
        key_id = os.environ.get(_ENV_KEY_ID) or (
            "env-" + hashlib.sha256(os.environ[_ENV_SECRET].encode()).hexdigest()[:8])
    else:
        key_id = _DEV_KEY_ID
    return SecretInfo(mode=mode, key_id=key_id, configured=configured)


def generate_secret() -> tuple[str, str]:
    """Generate a fresh (key_id, hex_secret) pair for the user to export. Never persisted."""
    raw = os.urandom(32)
    hex_secret = raw.hex()
    key_id = "key-" + hashlib.sha256(hex_secret.encode()).hexdigest()[:8]
    return key_id, hex_secret


def redact(secret_hex: str) -> str:
    """Show only a prefix so the secret is never fully displayed."""
    return secret_hex[:6] + "…" + f"({len(secret_hex)} hex chars)"
