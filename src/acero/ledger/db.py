"""Database engine/session management. SQLite by default (local-first)."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import Config, get_config, repo_root
from .models import Base


def make_engine(cfg: Config | None = None, *, echo: bool = False) -> Engine:
    cfg = cfg or get_config()
    url = cfg.abs_db_url()
    if url.startswith("sqlite:///"):
        path = url[len("sqlite:///"):]
        if path and path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    engine = create_engine(url, echo=echo, future=True)
    return engine


def init_db(engine: Engine) -> None:
    """Create all tables. Idempotent. (Alembic scaffolding lives in infra/ for prod.)"""
    Base.metadata.create_all(engine)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def default_session_factory(cfg: Config | None = None) -> sessionmaker[Session]:
    engine = make_engine(cfg)
    init_db(engine)
    return make_session_factory(engine)


def workspace_dir(cfg: Config | None = None) -> Path:
    cfg = cfg or get_config()
    d = repo_root() / cfg.storage.workspace_dir
    d.mkdir(parents=True, exist_ok=True)
    return d
