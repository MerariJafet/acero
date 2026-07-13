"""Time source. Centralised so tests can freeze time and provenance stays honest."""

from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(UTC)


def now_iso() -> str:
    return now().isoformat()
