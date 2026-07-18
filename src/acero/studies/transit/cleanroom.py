"""Clean-room reproduction of the transit analysis (Sprint 24 §24.16).

Re-downloads the light curves into a FRESH cache directory, recomputes SHA-256
hashes, re-runs BOTH pipelines, and checks the recovered period and hashes match
the recorded manifest. The Dockerfile alongside defines the fully-isolated
container path; this function exercises the same steps in a clean local directory.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from . import data
from . import pipelines as pl

KEPLER8B_PERIOD = 3.52254


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def reproduce(fresh_cache: Path) -> dict[str, Any]:
    """Download to a fresh cache, recompute hashes, re-run pipelines; report drift."""
    fresh_cache.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    import urllib.request
    for kic, quarters in ((data.TARGET_KIC, data.TARGET_QUARTERS),
                          (data.CONTROL_KIC, data.CONTROL_QUARTERS)):
        for q in quarters:
            url = data._fits_url(kic, q)
            dest = fresh_cache / f"kplr{kic}-{q}_llc.fits"
            req = urllib.request.Request(url, headers={"User-Agent": "ACERO-cleanroom/2.1"})
            with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as out:
                out.write(r.read())
            hashes[dest.name] = _sha256(dest)

    # read the science series from the FRESH files (no shared cache/state)
    from astropy.io import fits

    def series(kic: str, quarters: list[str]) -> tuple[np.ndarray, np.ndarray]:
        import math
        t: list[float] = []
        fl: list[float] = []
        for q in quarters:
            with fits.open(fresh_cache / f"kplr{kic}-{q}_llc.fits") as hdul:
                d = hdul[1].data
                for tt, ff, qual in zip(d["TIME"], d["PDCSAP_FLUX"], d["SAP_QUALITY"],
                                        strict=False):
                    if int(qual) != 0 or math.isnan(float(tt)) or math.isnan(float(ff)):
                        continue
                    t.append(float(tt))
                    fl.append(float(ff))
        arr = np.array(fl)
        arr = arr / np.median(arr)
        return np.array(t), arr

    t, f = series(data.TARGET_KIC, data.TARGET_QUARTERS)
    a = pl.pipeline_a(t, f)
    b = pl.pipeline_b(t, f)
    frac_err = abs(a.period - KEPLER8B_PERIOD) / KEPLER8B_PERIOD

    # compare against the recorded manifest hashes if present
    drift: list[str] = []
    manifest_path = data.repo_root() / "research" / "artifacts" / "transit" / "data_manifests.json"
    if manifest_path.exists():
        import json
        recorded = {m["source_url"].split("/")[-1]: m["sha256"]
                    for m in json.loads(manifest_path.read_text())["manifests"]}
        for name, h in hashes.items():
            if name in recorded and recorded[name] != h:
                drift.append(name)

    return {
        "fresh_cache": str(fresh_cache),
        "n_files": len(hashes), "hashes": hashes, "hash_drift": drift,
        "pipeline_A_period": round(a.period, 5), "pipeline_B_period": round(b.period, 5),
        "period_frac_error": round(frac_err, 5),
        "reproduced_known_period": frac_err < 0.005,
        "no_hash_drift": len(drift) == 0,
        "note": "recovery of a known transit; NOT a discovery, NOT external replication",
    }
