"""Data acquisition + manifest for the transit robustness program.

Downloads public Kepler long-cadence light curves from the MAST archive into a
gitignored cache, and records a full provenance manifest per file (URL, provider,
date, license, size, SHA-256, schema, reference, terms). No paid API, no account.

Kepler data are in the public domain (NASA); see the terms recorded below.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ...core.config import repo_root

MAST_BASE = "https://archive.stsci.edu/pub/kepler/lightcurves"

# Science target: Kepler-8 (KIC 6922244) — confirmed hot Jupiter Kepler-8b,
# P≈3.5225 d, depth≈0.9%, T≈3.2 h; well sampled by 29.4-min long cadence.
TARGET_KIC = "006922244"
TARGET_NAME = "Kepler-8"
# Control: KIC 6116048 — an asteroseismic solar-type star with NO transiting
# planet; used to check the pipeline does not manufacture Kepler-8b's signal.
CONTROL_KIC = "006116048"
CONTROL_NAME = "KIC 6116048 (quiet control)"

# A few quarters (long cadence). Keeping the volume tiny (<2 MB total).
TARGET_QUARTERS = ["2009259160929", "2009350155506", "2010078095331"]
CONTROL_QUARTERS = ["2009259160929"]

LICENSE = "Public domain (NASA / Kepler mission data)"
TERMS = ("Kepler mission data are public domain; NASA requests acknowledgement of "
         "the mission and the MAST archive. No account or paid API used.")
REFERENCE = ("Jenkins et al. 2010, ApJL 724, 1108 (Kepler-8b discovery); "
             "Kepler Data Processing Handbook (KSCI-19081).")


def cache_dir() -> Path:
    d = repo_root() / "research" / "cache" / "kepler"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fits_url(kic: str, quarter: str) -> str:
    return f"{MAST_BASE}/{kic[:4]}/{kic}/kplr{kic}-{quarter}_llc.fits"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class TransitDatasetManifest:
    mission: str
    target: str
    kic: str
    role: str                      # "science" | "control"
    sector_or_quarter: str
    cadence: str
    pipeline: str
    time_column: str
    flux_column: str
    error_column: str
    quality_column: str
    license: str
    source_url: str
    sha256: str
    downloaded_at: str
    size_bytes: int
    missingness: float
    known_artifacts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def download_fits(kic: str, quarter: str, *, force: bool = False) -> Path:
    """Download one quarter FITS into the gitignored cache (idempotent)."""
    dest = cache_dir() / f"kplr{kic}-{quarter}_llc.fits"
    if dest.exists() and not force and dest.stat().st_size > 0:
        return dest
    url = _fits_url(kic, quarter)
    req = urllib.request.Request(url, headers={"User-Agent": "ACERO-local-research/2.1"})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as out:
        out.write(r.read())
    return dest


def _read_lightcurve(path: Path) -> dict[str, Any]:
    """Read (time, flux, flux_err, quality) from a Kepler long-cadence FITS."""
    from astropy.io import fits  # local import: heavy dependency

    with fits.open(path) as hdul:
        data = hdul[1].data
        time = list(map(float, data["TIME"]))
        flux = list(map(float, data["PDCSAP_FLUX"]))
        err = list(map(float, data["PDCSAP_FLUX_ERR"]))
        quality = list(map(int, data["SAP_QUALITY"]))
    return {"time": time, "flux": flux, "flux_err": err, "quality": quality}


def _missingness(flux: list[float]) -> float:
    import math

    n = len(flux)
    if not n:
        return 1.0
    miss = sum(1 for v in flux if v is None or (isinstance(v, float) and math.isnan(v)))
    return round(miss / n, 4)


def acquire(kic: str, name: str, quarter: str, role: str, *, downloaded_at: str
            ) -> tuple[Path, TransitDatasetManifest]:
    """Download + build a manifest for one quarter (records provenance)."""
    path = download_fits(kic, quarter)
    lc = _read_lightcurve(path)
    manifest = TransitDatasetManifest(
        mission="Kepler", target=name, kic=kic, role=role,
        sector_or_quarter=f"Q@{quarter}", cadence="long (29.4 min)",
        pipeline="PDCSAP (Kepler DR25)", time_column="TIME",
        flux_column="PDCSAP_FLUX", error_column="PDCSAP_FLUX_ERR",
        quality_column="SAP_QUALITY", license=LICENSE, source_url=_fits_url(kic, quarter),
        sha256=_sha256(path), downloaded_at=downloaded_at,
        size_bytes=path.stat().st_size, missingness=_missingness(lc["flux"]),
        known_artifacts=["quarter boundaries / rolls", "safe-mode gaps",
                         "thermal transients", "cosmic rays flagged in SAP_QUALITY"])
    return path, manifest


def acquire_program(downloaded_at: str) -> dict[str, Any]:
    """Acquire target + control quarters; write manifests to the artifacts dir."""
    manifests: list[dict[str, Any]] = []
    for q in TARGET_QUARTERS:
        _, m = acquire(TARGET_KIC, TARGET_NAME, q, "science", downloaded_at=downloaded_at)
        manifests.append(m.as_dict())
    for q in CONTROL_QUARTERS:
        _, m = acquire(CONTROL_KIC, CONTROL_NAME, q, "control", downloaded_at=downloaded_at)
        manifests.append(m.as_dict())
    out = repo_root() / "research" / "artifacts" / "transit" / "data_manifests.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {"license": LICENSE, "terms": TERMS, "reference": REFERENCE,
           "total_bytes": sum(m["size_bytes"] for m in manifests),
           "manifests": manifests}
    out.write_text(json.dumps(doc, indent=2))
    return doc


def load_series(kic: str, quarters: list[str]) -> dict[str, list[float]]:
    """Concatenate quarters into one cleaned (time, flux, err) series (NaNs dropped)."""
    import math

    time: list[float] = []
    flux: list[float] = []
    err: list[float] = []
    for q in quarters:
        path = download_fits(kic, q)
        lc = _read_lightcurve(path)
        for t, f, e, qual in zip(lc["time"], lc["flux"], lc["flux_err"],
                                 lc["quality"], strict=False):
            if qual != 0:
                continue
            if any(math.isnan(x) for x in (t, f, e)):
                continue
            time.append(t)
            flux.append(f)
            err.append(e)
    # normalise flux to a median of 1.0
    if flux:
        med = sorted(flux)[len(flux) // 2]
        flux = [f / med for f in flux]
        err = [e / med for e in err]
    return {"time": time, "flux": flux, "flux_err": err}
