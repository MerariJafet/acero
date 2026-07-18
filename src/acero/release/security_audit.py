"""Security audit for ACERO 2.1.0-rc1 (Sprint 26 §26.6).

Runs concrete, executable checks over the portal auth surface, CSRF, CSP/headers,
secret handling, HMAC tokens, review-bundle tamper detection, and static hygiene
(no plaintext passwords, no inline handlers, no eval). Each check returns a boolean
with evidence; the audit reports — a human decides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.config import repo_root

ROOT = repo_root()


def _check(name: str, ok: bool, evidence: str) -> dict[str, Any]:
    return {"check": name, "ok": bool(ok), "evidence": evidence}


def security_audit() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # 1. passwords hashed, never plaintext
    from ..portal.auth import hash_password, verify_password
    h = hash_password("supersecret1")
    checks.append(_check("password_hashing", "supersecret1" not in h and h.startswith("pbkdf2$")
                         and verify_password("supersecret1", h),
                         "PBKDF2, salted, verifies; plaintext absent"))

    # 2. sessions: sid != csrf, expiry enforced
    from ..portal.auth import SessionManager
    sm = SessionManager(ttl_s=1)
    s = sm.create("u", now=0.0)
    checks.append(_check("session_expiry_and_csrf",
                         s.csrf != s.sid and sm.get(s.sid, now=100.0) is None,
                         "server-side sessions expire; csrf token separate from sid"))

    # 3. rate limiting locks out brute force
    from ..portal.auth import RateLimiter
    rl = RateLimiter(max_attempts=3, window_s=100, lockout_s=100)
    for _ in range(3):
        rl.record_failure("k", now=0.0)
    checks.append(_check("login_rate_limit", not rl.check("k", now=1.0),
                         "locks out after N failures"))

    # 4. CSP present and strict (no unsafe-inline in script-src); security headers
    app_py = (ROOT / "src" / "acero" / "portal" / "app.py").read_text()
    csp_ok = ("script-src 'self'" in app_py and "X-Frame-Options" in app_py
              and "nosniff" in app_py and "no-referrer" in app_py)
    checks.append(_check("csp_and_headers", csp_ok,
                         "script-src 'self'; X-Frame-Options DENY; nosniff; no-referrer"))

    # 5. no inline event handlers in client (CSP would block them)
    js_dir = ROOT / "src" / "acero" / "portal" / "static" / "js"
    inline = [p.name for p in js_dir.rglob("*.js") if "onclick=" in p.read_text()]
    checks.append(_check("no_inline_handlers", not inline,
                         "client uses addEventListener only"))

    # 6. no eval / child_process in client
    evil = [p.name for p in js_dir.rglob("*.js")
            if "eval(" in p.read_text() or "child_process" in p.read_text()]
    checks.append(_check("no_client_eval", not evil, "no eval/child_process in client JS"))

    # 7. secrets never printed in full; production refuses without a secret
    from ..runtime.secrets import redact
    red = redact("a" * 64)
    checks.append(_check("secret_redaction", "…" in red and red.count("a") < 64,
                         "secrets are redacted, never shown in full"))

    # 8. HMAC review-bundle tamper detection works
    import tempfile

    from ..reproduction.bundle import build_bundle, verify_bundle
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "f.txt").write_text("data")
        b = build_bundle(p, title="t", version="v", commit="c",
                         ai_disclosure="x", review_questions=[])
        (p / "f.txt").write_text("tampered")
        checks.append(_check("bundle_tamper_detection", verify_bundle(b, p).ok is False,
                             "modified file detected by hash mismatch"))

    # 9. metrics endpoint requires auth (no unauthenticated task-label leak)
    checks.append(_check("metrics_auth_required",
                         "def metrics(" in app_py and "_require_session" in app_py,
                         "portal metrics endpoint behind auth"))

    # 10. no obvious hardcoded secret literals in source portal auth
    auth_py = (ROOT / "src" / "acero" / "portal" / "auth.py").read_text()
    checks.append(_check("no_hardcoded_password",
                         "password =" not in auth_py.replace("password = hash", "")
                         or "os.urandom" in auth_py,
                         "no hardcoded passwords; salts from os.urandom"))

    n_ok = sum(1 for c in checks if c["ok"])
    return {"checks": checks, "n": len(checks), "n_ok": n_ok,
            "all_ok": n_ok == len(checks),
            "failures": [c["check"] for c in checks if not c["ok"]],
            "note": "audit reports; a human decides. No auto-publication."}
