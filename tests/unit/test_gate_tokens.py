"""Sprint 11 tests: mutation tokens (single-use, scoped, replay-proof)."""

from __future__ import annotations

import pytest

from acero.epistemic_gate.tokens import MutationToken, TokenError, TokenRegistry


def _reg():
    return TokenRegistry(ttl_seconds=30)


def test_valid_token_passes():
    reg = _reg()
    tok = reg.issue(action="update_belief", project_id="p1", artifact_ids=("n1",))
    reg.validate(tok, action="update_belief", project_id="p1", artifact_ids=("n1",))


def test_wrong_action_fails():
    reg = _reg()
    tok = reg.issue(action="update_belief", project_id="p1")
    with pytest.raises(TokenError):
        reg.validate(tok, action="link", project_id="p1")


def test_wrong_project_fails():
    reg = _reg()
    tok = reg.issue(action="update_belief", project_id="p1")
    with pytest.raises(TokenError):
        reg.validate(tok, action="update_belief", project_id="p2")


def test_wrong_artifact_fails():
    reg = _reg()
    tok = reg.issue(action="update_belief", project_id="p1", artifact_ids=("n1",))
    with pytest.raises(TokenError):
        reg.validate(tok, action="update_belief", project_id="p1", artifact_ids=("n2",))


def test_replay_fails():
    reg = _reg()
    tok = reg.issue(action="a", project_id="p")
    reg.validate(tok, action="a", project_id="p")
    reg.spend(tok)
    with pytest.raises(TokenError):
        reg.validate(tok, action="a", project_id="p")
    assert reg.metrics()["replays_blocked"] == 1


def test_tampered_token_fails():
    reg = _reg()
    tok = reg.issue(action="a", project_id="p")
    tok.signature = "deadbeef"
    with pytest.raises(TokenError):
        reg.validate(tok, action="a", project_id="p")


def test_expired_token_fails():
    reg = TokenRegistry(ttl_seconds=-1)          # already expired
    tok = reg.issue(action="a", project_id="p")
    with pytest.raises(TokenError):
        reg.validate(tok, action="a", project_id="p")
    assert reg.metrics()["expired_blocked"] == 1


def test_revoked_token_fails():
    reg = _reg()
    tok = reg.issue(action="a", project_id="p")
    reg.revoke(tok.token_id)
    with pytest.raises(TokenError):
        reg.validate(tok, action="a", project_id="p")


def test_forged_signature_from_other_secret_fails():
    """A token whose signature was not produced by this registry's secret is rejected."""
    tok = MutationToken(token_id="x", action="a", project_id="p", artifact_ids=(),
                        rule_versions=(), issued_at="2026-01-01T00:00:00+00:00",
                        expires_at="2999-01-01T00:00:00+00:00", signature="forged")
    with pytest.raises(TokenError):
        _reg().validate(tok, action="a", project_id="p")


def test_token_redacts_signature_by_default():
    tok = _reg().issue(action="a", project_id="p")
    assert "signature" not in tok.as_dict()
    assert "signature" in tok.as_dict(redact=False)
