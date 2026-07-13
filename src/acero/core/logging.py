"""Structured logging via structlog, with a stdlib fallback."""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import structlog

    _HAS_STRUCTLOG = True
except Exception:  # pragma: no cover
    _HAS_STRUCTLOG = False

_configured = False


def configure_logging(level: str = "INFO", json: bool = True) -> None:
    global _configured
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=lvl, stream=sys.stderr, format="%(message)s")
    if _HAS_STRUCTLOG:
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
        ]
        processors.append(
            structlog.processors.JSONRenderer()
            if json
            else structlog.dev.ConsoleRenderer(colors=False)
        )
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(lvl),
            logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
            cache_logger_on_first_use=True,
        )
    _configured = True


def get_logger(name: str = "acero"):
    if not _configured:
        configure_logging()
    if _HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)
