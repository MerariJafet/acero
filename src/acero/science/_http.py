"""Tiny self-contained HTTP-JSON helper so the science package stays decoupled from the
rest of ACERO (only dependency is the standard library). Used by the replication finder's
live Zenodo search; injectable for tests."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

_UA = "ACERO-science/1.0"


def get_json(url: str, opener: Any | None = None, timeout: float = 25.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": _UA,
                                               "Accept": "application/json"})
    op = opener or urllib.request.urlopen
    with op(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))
