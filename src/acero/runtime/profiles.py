"""Configuration profiles (Sprint 22).

Named operating profiles declaring DB / sandbox / tokens / logging / network / limits /
providers / portal / datasets. `production-local` REFUSES to start with a development (ephemeral)
HMAC secret — it requires a configured ACERO_HMAC_SECRET. No profile enables paid services or
network by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UnsafeProfileStartError(RuntimeError):
    """Raised when a profile's startup preconditions are not met."""


@dataclass
class Profile:
    name: str
    db: str
    sandbox: str
    tokens: str
    logging: str
    network: str
    limits: dict[str, Any]
    providers: str
    portal: str
    datasets: str
    requires_configured_secret: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in
                ("name", "db", "sandbox", "tokens", "logging", "network", "providers",
                 "portal", "datasets", "requires_configured_secret")} | {"limits": self.limits}


PROFILES: dict[str, Profile] = {
    "development": Profile(
        "development", db="sqlite-local", sandbox="subprocess", tokens="ephemeral",
        logging="human", network="off", limits={"max_workers": 2},
        providers="mock", portal="on", datasets="gated"),
    "research": Profile(
        "research", db="sqlite-local", sandbox="docker", tokens="ephemeral",
        logging="json", network="gated-downloads", limits={"max_workers": 4},
        providers="mock|codex", portal="on", datasets="gated"),
    "review": Profile(
        "review", db="sqlite-local", sandbox="subprocess", tokens="ephemeral",
        logging="json", network="off", limits={"max_workers": 2},
        providers="mock", portal="on", datasets="read-only"),
    "production-local": Profile(
        "production-local", db="sqlite-or-postgres", sandbox="docker", tokens="signed",
        logging="json", network="gated-downloads", limits={"max_workers": 8},
        providers="mock|codex", portal="on", datasets="gated",
        requires_configured_secret=True),
    "test": Profile(
        "test", db="sqlite-memory", sandbox="subprocess", tokens="ephemeral",
        logging="off", network="off", limits={"max_workers": 1},
        providers="mock", portal="off", datasets="fixtures"),
}


def get_profile(name: str) -> Profile:
    if name not in PROFILES:
        raise KeyError(f"unknown profile {name!r}; have {sorted(PROFILES)}")
    return PROFILES[name]


def check_startup(name: str, *, secret_configured: bool) -> None:
    """Raise UnsafeProfileStartError if the profile cannot safely start.

    production-local refuses to run with a development (unconfigured/ephemeral) secret.
    """
    profile = get_profile(name)
    if profile.requires_configured_secret and not secret_configured:
        raise UnsafeProfileStartError(
            f"profile '{name}' requires a configured ACERO_HMAC_SECRET "
            "(run 'acero secrets init'); refusing to start with a development secret")
