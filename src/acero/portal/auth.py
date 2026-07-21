"""Local portal authentication (Sprint 23).

Local-first, single-tenant auth: one or a few local users, PBKDF2 password hashes
(never plaintext), server-side sessions keyed by a random id carried in an
httponly + samesite=strict cookie, double-submit CSRF tokens on mutating requests,
per-user login rate limiting, and manual local recovery.

Deliberately NOT built: multi-tenant orgs, password reset emails, OAuth, remote
identity. This is a local scientific control panel, not a public SaaS.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets as _secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.config import repo_root

# --- password hashing ------------------------------------------------------

_PBKDF2_ROUNDS = 200_000
_SALT_BYTES = 16


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return ``pbkdf2$<rounds>$<salt_hex>$<hash_hex>`` — never the plaintext."""
    if not password or len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    salt = salt or os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${_PBKDF2_ROUNDS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verify against a stored ``pbkdf2$...`` string."""
    try:
        scheme, rounds_s, salt_hex, hash_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), int(rounds_s))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), hash_hex)


# --- user store (local file, gitignored) -----------------------------------

def _users_path() -> Path:
    override = os.environ.get("ACERO_PORTAL_USERS")
    if override:
        return Path(override)
    return repo_root() / "acero_data" / "portal_users.json"


class UserStore:
    """A tiny local JSON user store: ``{username: {"password": "pbkdf2$..."}}``."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _users_path()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text() or "{}")

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.path)
        os.chmod(self.path, 0o600)

    def create_user(self, username: str, password: str, *, overwrite: bool = False) -> None:
        if not username or not username.isidentifier():
            raise ValueError("username must be a simple identifier")
        data = self._load()
        if username in data and not overwrite:
            raise ValueError(f"user '{username}' already exists")
        data[username] = {"password": hash_password(password)}
        self._save(data)

    def verify(self, username: str, password: str) -> bool:
        rec = self._load().get(username)
        if not rec:
            # still spend time to reduce username-enumeration timing signal
            verify_password(password, "pbkdf2$1$00$00")
            return False
        return verify_password(password, rec["password"])

    def exists(self, username: str) -> bool:
        return username in self._load()

    def usernames(self) -> list[str]:
        return sorted(self._load().keys())


# --- rate limiting ---------------------------------------------------------

@dataclass
class _Attempts:
    count: int = 0
    first_at: float = 0.0
    locked_until: float = 0.0


class RateLimiter:
    """Per-key fixed-window limiter with lockout (login brute-force defense)."""

    def __init__(self, *, max_attempts: int = 5, window_s: float = 300.0,
                 lockout_s: float = 300.0) -> None:
        self.max_attempts = max_attempts
        self.window_s = window_s
        self.lockout_s = lockout_s
        self._state: dict[str, _Attempts] = {}

    def check(self, key: str, *, now: float | None = None) -> bool:
        """True if allowed. Does not record — call ``record_failure`` on a bad login."""
        now = time.time() if now is None else now
        a = self._state.get(key)
        if a and a.locked_until > now:
            return False
        return True

    def record_failure(self, key: str, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        a = self._state.setdefault(key, _Attempts())
        if now - a.first_at > self.window_s:
            a.count, a.first_at = 0, now
        a.count += 1
        if a.count >= self.max_attempts:
            a.locked_until = now + self.lockout_s

    def record_success(self, key: str) -> None:
        self._state.pop(key, None)

    def retry_after(self, key: str, *, now: float | None = None) -> int:
        now = time.time() if now is None else now
        a = self._state.get(key)
        return max(0, int(a.locked_until - now)) if a else 0


# --- sessions --------------------------------------------------------------

@dataclass
class Session:
    sid: str
    user: str
    csrf: str
    created_at: float
    expires_at: float

    def valid(self, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return now < self.expires_at


@dataclass
class SessionManager:
    """Server-side sessions for the local portal.

    The session id is a 256-bit random token; the client only ever holds it in an
    httponly cookie, so client JS cannot read it. CSRF uses a separate token that
    the client DOES read and echoes back in a header (double-submit).

    If ``persist_path`` is set, sessions are stored on disk so a portal restart does
    NOT log the user out (local-first convenience). Without it, sessions are purely
    in-memory (used by tests).
    """

    ttl_s: float = 8 * 3600.0
    persist_path: Path | None = None
    _sessions: dict[str, Session] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.persist_path:
            self._load()

    def _load(self) -> None:
        try:
            if self.persist_path and self.persist_path.exists():
                data = json.loads(self.persist_path.read_text() or "{}")
                now = time.time()
                for sid, s in data.items():
                    if float(s.get("expires_at", 0)) > now:
                        self._sessions[sid] = Session(**s)
        except Exception:  # noqa: BLE001 - a corrupt file just means "no sessions"
            self._sessions = {}

    def _save(self) -> None:
        if not self.persist_path:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {sid: vars(s) for sid, s in self._sessions.items()}
            tmp = self.persist_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload))
            tmp.replace(self.persist_path)
            os.chmod(self.persist_path, 0o600)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass

    def create(self, user: str, *, now: float | None = None) -> Session:
        now = time.time() if now is None else now
        sid = _secrets.token_urlsafe(32)
        sess = Session(sid=sid, user=user, csrf=_secrets.token_urlsafe(24),
                       created_at=now, expires_at=now + self.ttl_s)
        self._sessions[sid] = sess
        self._save()
        return sess

    def get(self, sid: str | None, *, now: float | None = None) -> Session | None:
        if not sid:
            return None
        sess = self._sessions.get(sid)
        if sess is None:
            return None
        if not sess.valid(now=now):
            self._sessions.pop(sid, None)
            self._save()
            return None
        return sess

    def invalidate(self, sid: str | None) -> None:
        if sid and sid in self._sessions:
            self._sessions.pop(sid, None)
            self._save()

    def cleanup(self, *, now: float | None = None) -> int:
        now = time.time() if now is None else now
        dead = [s for s, v in self._sessions.items() if not v.valid(now=now)]
        for s in dead:
            self._sessions.pop(s, None)
        if dead:
            self._save()
        return len(dead)
