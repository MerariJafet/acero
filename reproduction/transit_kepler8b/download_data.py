"""Download public Kepler light curves and record SHA-256 — standalone (no ACERO)."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

BASE = "https://archive.stsci.edu/pub/kepler/lightcurves"
TARGET_KIC = "006922244"          # Kepler-8
CONTROL_KIC = "006116048"         # quiet control
TARGET_QUARTERS = ["2009259160929", "2009350155506", "2010078095331"]
CONTROL_QUARTERS = ["2009259160929"]


def fits_url(kic: str, quarter: str) -> str:
    return f"{BASE}/{kic[:4]}/{kic}/kplr{kic}-{quarter}_llc.fits"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_all(dest_dir: Path) -> dict[str, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = {}
    for kic, quarters in ((TARGET_KIC, TARGET_QUARTERS), (CONTROL_KIC, CONTROL_QUARTERS)):
        for q in quarters:
            dest = dest_dir / f"kplr{kic}-{q}_llc.fits"
            if not dest.exists() or dest.stat().st_size == 0:
                req = urllib.request.Request(fits_url(kic, q),
                                             headers={"User-Agent": "kepler8b-repro/1.0"})
                with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as out:
                    out.write(r.read())
            hashes[dest.name] = sha256(dest)
    return hashes


if __name__ == "__main__":
    hs = download_all(Path("./_data"))
    print(json.dumps(hs, indent=2))
