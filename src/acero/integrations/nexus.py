"""NEXUS connector — reads the researcher's real finances from the NEXUS finance
app so ACERO's economic mode reasons over FACTS, never invented numbers.

Resolution order (honest, best-effort):
  1. NEXUS HTTP API (FastAPI at ACERO_NEXUS_URL; bearer token or user/pass login).
  2. A local snapshot file (acero_data/economics/nexus_snapshot.json) — manual
     import, or a push from NEXUS — so the mode works offline.
  3. Nothing available → {"available": False}. We NEVER fabricate figures.

Everything is normalized to one canonical snapshot the advisor can read:
  {available, source, period, currency, income, expenses, net,
   expenses_by_category: [{category, amount}], accounts: [{name, balance}],
   fetched_at, raw?}

The connector is READ-ONLY: it never moves money or changes NEXUS state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root
from ..core.workspace import data_path

DEFAULT_URL = os.environ.get("ACERO_NEXUS_URL", "http://localhost:8000").rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("ACERO_NEXUS_TIMEOUT", "6"))


def snapshot_path() -> Path:
    env = os.environ.get("ACERO_ECON_ROOT", "").strip()
    root = Path(env) if env else data_path("datos/economics", legacy=repo_root() / "acero_data" / "economics")
    return root / "nexus_snapshot.json"


def _empty(reason: str) -> dict[str, Any]:
    return {"available": False, "source": "none", "reason": reason,
            "income": None, "expenses": None, "net": None,
            "expenses_by_category": [], "accounts": [], "fetched_at": now_iso()}


def _num(v: Any) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def normalize(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Map a NEXUS /summary-style payload into ACERO's canonical snapshot.
    Defensive: NEXUS field names vary, so we probe several common keys and keep
    the raw payload for transparency. Missing fields stay None (not zero)."""
    def pick(*keys: str) -> Any:
        for k in keys:
            if isinstance(raw, dict) and raw.get(k) is not None:
                return raw[k]
        return None

    cats_raw = pick("expenses_by_category", "by_category", "categories", "spend_by_category") or []
    cats: list[dict[str, Any]] = []
    if isinstance(cats_raw, dict):
        cats_raw = [{"category": k, "amount": v} for k, v in cats_raw.items()]
    for c in cats_raw if isinstance(cats_raw, list) else []:
        if isinstance(c, dict):
            cats.append({"category": str(c.get("category") or c.get("name") or "?")[:60],
                         "amount": _num(c.get("amount") or c.get("total") or c.get("value"))})
    accts_raw = pick("accounts", "balances") or []
    accts: list[dict[str, Any]] = []
    for a in accts_raw if isinstance(accts_raw, list) else []:
        if isinstance(a, dict):
            accts.append({"name": str(a.get("name") or a.get("account") or "?")[:60],
                          "balance": _num(a.get("balance") or a.get("amount"))})
    income = _num(pick("income", "total_income", "ingresos"))
    expenses = _num(pick("expenses", "total_expenses", "gastos", "spend"))
    net = _num(pick("net", "balance", "net_flow"))
    if net is None and income is not None and expenses is not None:
        net = round(income - expenses, 2)
    return {"available": True, "source": source,
            "period": pick("period", "range", "month"),
            "currency": pick("currency", "moneda") or "MXN",
            "income": income, "expenses": expenses, "net": net,
            "expenses_by_category": cats, "accounts": accts,
            "fetched_at": now_iso(), "raw": raw}


class NexusConnector:
    """Read-only client. `http` is injectable (a callable(method,url,headers)->dict)
    for tests; by default uses httpx."""

    def __init__(self, base_url: str = DEFAULT_URL, *, token: str | None = None,
                 http: Any = None) -> None:
        self.base = base_url.rstrip("/")
        self.token = token or os.environ.get("ACERO_NEXUS_TOKEN")
        self._http = http

    def _get(self, path: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        if self._http is not None:
            return self._http("GET", self.base + path, headers)
        import httpx
        r = httpx.get(self.base + path, headers=headers, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.json()

    def fetch_snapshot(self) -> dict[str, Any]:
        """API first, then the local snapshot file, then honest emptiness."""
        # 1) live API
        for path in ("/summary", "/transactions/summary", "/balance"):
            try:
                data = self._get(path)
                if isinstance(data, dict) and data:
                    return normalize(data, source=f"nexus-api{path}")
            except Exception:  # noqa: BLE001 - try the next path / fallback
                continue
        # 2) local snapshot file (manual import or NEXUS push)
        f = snapshot_path()
        if f.exists():
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                if raw.get("available") and "expenses_by_category" in raw:
                    return raw                       # already-canonical snapshot
                return normalize(raw, source="snapshot-file")
            except Exception as exc:  # noqa: BLE001
                return _empty(f"snapshot ilegible: {exc}")
        # 3) nothing — never fabricate
        return _empty("NEXUS no disponible (ni API en "
                      f"{self.base} ni snapshot en {f}). Conecta NEXUS "
                      "(ACERO_NEXUS_URL/TOKEN) o importa un snapshot.")


def fetch_snapshot() -> dict[str, Any]:
    return NexusConnector().fetch_snapshot()
