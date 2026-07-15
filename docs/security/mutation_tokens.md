# Mutation Tokens (Sprint 11)

A protected scientific mutation requires a token minted only after a valid gate PASS. A
token is HMAC-signed over its fields (id, action, project, artifacts, rule versions, issue/
expiry) with a per-process secret. It is: action-specific, artifact-limited, short-lived
(TTL), single-use (spent after the mutation), and non-transferable. Validation rejects a
tampered, expired, replayed, revoked, wrong-action, wrong-project, or wrong-artifact token.
The token authorises only the exact mutation it was minted for and never permits a new one.
The secret is per-process (tokens do not survive a restart — by design). Tokens are redacted
(signature hidden) in any external representation.
