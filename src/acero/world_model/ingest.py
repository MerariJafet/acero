"""Real astronomy dataset ingestion (NASA Exoplanet Archive) → World Model change.

Downloads a small, open, verifiable dataset (planet orbital period, semi-major axis,
stellar mass), records it as a Dataset node with license/provenance/hash, and TESTS
the belief "Kepler's third law holds (P² = a³ / M in solar units)" against REAL data,
updating the belief's support. The goal is to verify the World Model changes
correctly with real data — NOT to claim any discovery.
"""

from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.hashing import hash_file, hash_text
from .edges import EdgeType
from .graph import WorldModel
from .nodes import NodeType

TAP_URL = (
    "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
    "select+pl_name,pl_orbper,pl_orbsmax,st_mass+from+ps+where+pl_orbper+is+not+null+"
    "and+pl_orbsmax+is+not+null+and+st_mass+is+not+null+and+default_flag=1&format=csv"
)
LICENSE = "Public domain (NASA/IPAC/Caltech Exoplanet Archive)"
REFERENCE = "NASA Exoplanet Archive (Akeson et al. 2013, PASP 125, 989)"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB cap — far below the 500 MB policy limit


def download_exoplanets(dest: str | Path, *, authorized: bool, url: str = TAP_URL,
                        max_bytes: int = MAX_BYTES) -> dict[str, Any]:
    """Download the dataset. Requires explicit human authorization (policy)."""
    if not authorized:
        raise PermissionError(
            "Downloading external data requires explicit authorization "
            "(data_access policy). Pass authorized=True.")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 - fixed https host
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"Download exceeds {max_bytes} bytes cap")
    dest.write_bytes(data)
    return {"path": str(dest), "bytes": len(data), "sha256": hash_file(dest),
            "url": url, "license": LICENSE, "reference": REFERENCE,
            "downloaded_at": now_iso()}


def _parse_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for r in reader:
        try:
            p = float(r["pl_orbper"])
            a = float(r["pl_orbsmax"])
            m = float(r["st_mass"])
        except (TypeError, ValueError, KeyError):
            continue
        if p > 0 and a > 0 and m > 0:
            rows.append({"name": r.get("pl_name", ""), "P_days": p, "a_AU": a, "M_sun": m})
    return rows


def kepler_test(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Test P[yr]² ≈ a³ / M on real data. Returns fit quality + deviating planets."""
    import numpy as np

    P_yr = np.array([r["P_days"] / 365.25 for r in rows])
    a = np.array([r["a_AU"] for r in rows])
    m = np.array([r["M_sun"] for r in rows])
    lhs = P_yr ** 2
    rhs = a ** 3 / m
    # Log-log regression: log(lhs) = slope * log(rhs) + intercept; Kepler => slope≈1.
    x = np.log10(rhs)
    y = np.log10(lhs)
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    ratio = lhs / rhs
    within = float(np.mean((ratio > 0.5) & (ratio < 2.0)))
    deviating = [rows[i]["name"] for i in np.argsort(-np.abs(np.log(ratio)))[:5]]
    return {"n": len(rows), "slope": round(float(slope), 4),
            "intercept": round(float(intercept), 4), "r2": round(r2, 4),
            "fraction_within_2x": round(within, 4), "most_deviating": deviating}


def ingest_exoplanets(wm: WorldModel, csv_path: str | Path, *, program_id: str | None = None,
                      manifest: dict[str, Any] | None = None, sample_observations: int = 10,
                      actor: str = "human") -> dict[str, Any]:
    text = Path(csv_path).read_text(encoding="utf-8", errors="replace")
    rows = _parse_rows(text)
    if not rows:
        raise ValueError("No usable rows in the exoplanet dataset")
    manifest = manifest or {"sha256": hash_text(text), "license": LICENSE,
                            "reference": REFERENCE, "url": TAP_URL}

    dataset = wm.create(NodeType.DATASET, "NASA Exoplanet Archive (P, a, M)",
                        domain="astronomy", program_id=program_id,
                        data={"n_rows": len(rows), "sha256": manifest.get("sha256"),
                              "license": manifest.get("license"),
                              "reference": manifest.get("reference"),
                              "url": manifest.get("url"), "ingested_at": now_iso()})
    for r in rows[:sample_observations]:
        obs = wm.create(NodeType.OBSERVATION, f"{r['name']}: P={r['P_days']:.2f}d a={r['a_AU']}AU",
                        domain="astronomy", program_id=program_id, data=r)
        wm.link(EdgeType.OBSERVED_IN, obs.id, dataset.id)

    fit = kepler_test(rows)

    # The belief: Kepler's third law. Real data supports it (or not) → update.
    law = wm.get_or_create(NodeType.LAW, "Kepler's third law (P^2 = a^3 / M)",
                           domain="astronomy", program_id=program_id,
                           data={"subject": "orbital-period-vs-distance", "stance": "holds",
                                 "form": "P[yr]^2 = a[AU]^3 / M[Msun]"})
    ev = wm.create(NodeType.EVIDENCE,
                   f"Real exoplanet data: log-log slope={fit['slope']}, R²={fit['r2']}",
                   domain="astronomy", program_id=program_id, data=fit)
    wm.link(EdgeType.SUPPORTS, ev.id, law.id, weight=fit["r2"], confidence=fit["r2"])
    wm.link(EdgeType.DERIVED_FROM, ev.id, dataset.id)
    # Evidence strength from R²; distinct source = this dataset.
    wm.update_belief(law.id, event="dataset_test", evidence=max(0.0, fit["r2"]),
                     replication=1, source=dataset.id, actor=actor)

    return {"dataset_id": dataset.id, "law_id": law.id, "evidence_id": ev.id,
            "fit": fit, "n_rows": len(rows)}
