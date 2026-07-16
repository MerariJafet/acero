"""Programmatic Alembic API (Sprint 22).

Wraps alembic.command so `acero db upgrade/downgrade/current/history/check` work without an
external alembic.ini on disk — the config is built in-process against the configured DB URL and
this package's versions/ directory.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from ..core.config import get_config

_HEAD = "0001_baseline"


def _cfg(url: str | None = None) -> AlembicConfig:
    here = Path(__file__).parent
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(here))
    cfg.set_main_option("sqlalchemy.url", url or get_config().abs_db_url())
    return cfg


def upgrade(url: str | None = None, *, revision: str = "head") -> str:
    command.upgrade(_cfg(url), revision)
    return current(url) or "unknown"


def downgrade(url: str | None = None, *, revision: str = "base") -> str:
    command.downgrade(_cfg(url), revision)
    return current(url) or "base"


def current(url: str | None = None) -> str | None:
    resolved = url or get_config().abs_db_url()
    eng = create_engine(resolved, future=True)
    with eng.connect() as conn:
        ctx = MigrationContext.configure(conn)
        return ctx.get_current_revision()


def head() -> str:
    return _HEAD


def history(url: str | None = None) -> list[dict[str, Any]]:
    script = ScriptDirectory.from_config(_cfg(url))
    return [{"revision": s.revision, "down_revision": s.down_revision,
             "doc": (s.doc or "").splitlines()[0] if s.doc else ""}
            for s in script.walk_revisions()]


def check(url: str | None = None) -> dict[str, Any]:
    """Report whether the DB is at head, behind, or unmanaged."""
    cur = current(url)
    at_head = cur == _HEAD
    return {"current": cur, "head": _HEAD, "at_head": at_head,
            "status": ("up_to_date" if at_head
                       else "unmanaged (run 'acero db upgrade')" if cur is None
                       else "behind (run 'acero db upgrade')")}


def stamp_head(url: str | None = None) -> None:
    """Stamp an existing (create_all) DB at head without recreating tables."""
    command.stamp(_cfg(url), _HEAD)


def render_history(url: str | None = None) -> str:
    buf = io.StringIO()
    for h in history(url):
        buf.write(f"{h['revision']} (down={h['down_revision']}): {h['doc']}\n")
    return buf.getvalue()
