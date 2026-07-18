"""Review bundle builder + tamper detection (Sprint 25).

A review bundle is a self-describing manifest binding a set of files to a version,
a commit, and per-file SHA-256 hashes, plus an AI disclosure and declared review
questions. Tamper detection recomputes hashes and flags any mismatch, missing file,
version/commit drift, or (optional) bad signature. The system RECORDS; it never
auto-accepts a review.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class ReviewBundle:
    title: str
    version: str
    commit: str
    files: dict[str, str]                 # relative path -> sha256
    ai_disclosure: str
    review_questions: list[str] = field(default_factory=list)
    identity_declared: str = ""
    conflicts_declared: str = ""
    license: str = "Apache-2.0"
    is_discovery: bool = False
    signature: str | None = None          # optional HMAC over the manifest

    def manifest_bytes(self) -> bytes:
        d = asdict(self)
        d.pop("signature", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, secret: bytes) -> None:
        self.signature = hmac.new(secret, self.manifest_bytes(), hashlib.sha256).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_bundle(root: Path, *, title: str, version: str, commit: str,
                 ai_disclosure: str, review_questions: list[str],
                 include: list[str] | None = None) -> ReviewBundle:
    """Hash every included file under ``root`` into a bundle manifest."""
    files: dict[str, str] = {}
    names = include or [p.name for p in sorted(root.iterdir()) if p.is_file()]
    for name in names:
        p = root / name
        if p.is_file():
            files[name] = _sha256_file(p)
    return ReviewBundle(title=title, version=version, commit=commit, files=files,
                        ai_disclosure=ai_disclosure, review_questions=review_questions)


@dataclass
class TamperReport:
    ok: bool
    missing: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    version_mismatch: bool = False
    commit_mismatch: bool = False
    signature_valid: bool | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_bundle(bundle: ReviewBundle, root: Path, *, expected_version: str | None = None,
                  expected_commit: str | None = None, secret: bytes | None = None
                  ) -> TamperReport:
    """Recompute hashes and detect tampering. Never trusts the bundle on its word."""
    missing: list[str] = []
    modified: list[str] = []
    for name, recorded in bundle.files.items():
        p = root / name
        if not p.is_file():
            missing.append(name)
            continue
        if _sha256_file(p) != recorded:
            modified.append(name)
    version_mismatch = expected_version is not None and bundle.version != expected_version
    commit_mismatch = expected_commit is not None and bundle.commit != expected_commit
    sig_valid: bool | None = None
    if secret is not None:
        if not bundle.signature:
            sig_valid = False
        else:
            want = hmac.new(secret, bundle.manifest_bytes(), hashlib.sha256).hexdigest()
            sig_valid = hmac.compare_digest(want, bundle.signature)
    ok = (not missing and not modified and not version_mismatch and not commit_mismatch
          and sig_valid is not False)
    return TamperReport(ok=ok, missing=missing, modified=modified,
                        version_mismatch=version_mismatch, commit_mismatch=commit_mismatch,
                        signature_valid=sig_valid)
