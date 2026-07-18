# ACERO 2.1.0-rc1 — Security

Run `acero security-audit` (10/10 checks). Summary:

## Portal authentication
- Passwords hashed with **PBKDF2** (200k rounds, per-user salt); never plaintext.
- Server-side sessions; 256-bit session id in an httponly, `SameSite=Strict`
  cookie (`Secure` configurable); CSRF token separate from the session id.
- **CSRF** double-submit required on every mutating endpoint.
- **Rate limiting** with lockout on failed logins.
- All `/portal/api/*` require a session except login/session; metrics behind auth.

## Headers / CSP
- `Content-Security-Policy: script-src 'self'` (no `unsafe-inline`, no eval),
  `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`.
- Client uses `addEventListener` only — no inline handlers (verified in a real browser).

## Secrets / tokens
- HMAC mutation-token secret from env; never in Git; redacted in all output.
- Production profile refuses to start signing without a configured secret.
- Runtime task rows redacted (no token/secret/signature fields exposed).

## Review bundles
- SHA-256 per-file hashes + version + commit binding; optional HMAC signature;
  tamper detection flags modified/missing files, version/commit drift, bad signatures.

## Sandbox / filesystem / data
- Execution via subprocess/docker sandbox; datasets are public/public-domain with
  recorded license + hash; download caches gitignored.

## Dependencies
- Added `astropy` (public, widely used). No paid services/APIs. No `node_modules`
  shipped (Playwright is a dev/test-only dependency).
