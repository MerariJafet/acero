"""Self-contained clean-room reproduction — NO ACERO imports.

Downloads Kepler-8 public light curves, recomputes SHA-256, runs an independent
BLS period search, and prints the recovered period. Depends only on numpy, scipy
and astropy. Proves the transit recovery reproduces without any ACERO internal
state (DB, World Model, secrets, caches). Recovering a KNOWN transit is not a
discovery.
"""

from __future__ import annotations

import hashlib
import math
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.timeseries import BoxLeastSquares

BASE = "https://archive.stsci.edu/pub/kepler/lightcurves"
KIC = "006922244"                         # Kepler-8
QUARTERS = ["2009259160929", "2009350155506", "2010078095331"]
KNOWN_PERIOD = 3.52254


def fetch(kic: str, quarter: str, dest: Path) -> str:
    url = f"{BASE}/{kic[:4]}/{kic}/kplr{kic}-{quarter}_llc.fits"
    req = urllib.request.Request(url, headers={"User-Agent": "cleanroom/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as out:
        blob = r.read()
        out.write(blob)
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        cache = Path(td)
        time: list[float] = []
        flux: list[float] = []
        for q in QUARTERS:
            dest = cache / f"kplr{KIC}-{q}_llc.fits"
            h = fetch(KIC, q, dest)
            print(f"downloaded {dest.name} sha256={h[:16]}…")
            with fits.open(dest) as hdul:
                d = hdul[1].data
                for tt, ff, qual in zip(d["TIME"], d["PDCSAP_FLUX"], d["SAP_QUALITY"],
                                        strict=False):
                    if int(qual) != 0 or math.isnan(float(tt)) or math.isnan(float(ff)):
                        continue
                    time.append(float(tt))
                    flux.append(float(ff))
        t = np.array(time)
        f = np.array(flux)
        f = f / np.median(f)
        # simple median detrend
        n = len(f)
        half = 25
        trend = np.array([np.median(f[max(0, i - half):min(n, i + half + 1)]) for i in range(n)])
        det = f / trend
        model = BoxLeastSquares(t, det)
        periods = np.linspace(0.5, 8.0, 4000)
        res = model.power(periods, [0.05, 0.1, 0.15, 0.2])
        best = float(res.period[int(np.argmax(res.power))])
        frac = abs(best - KNOWN_PERIOD) / KNOWN_PERIOD
        print(f"recovered period = {best:.5f} d  (known {KNOWN_PERIOD} d, frac err {frac:.5f})")
        print(f"points used = {n}")
        ok = frac < 0.005
        print("REPRODUCED_KNOWN_TRANSIT" if ok else "DID_NOT_REPRODUCE")
        print("NOTE: recovering a known transit is NOT a discovery.")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
