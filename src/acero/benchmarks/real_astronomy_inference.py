"""Real astronomy inference on the SILSO monthly sunspot number.

A genuine, tiny, public-domain astronomical time series (since 1749) with a ~11-year
quasi-cycle. We detect periodicity, distinguish periodic / quasiperiodic / noise,
recognise gaps, look for a low-activity regime, and record uncertainty — while stating
that the physical DYNAMO mechanism cannot be inferred from this series alone. NOT a
discovery.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from ..core.clock import now_iso
from ..core.hashing import hash_file, hash_text

URL = "https://www.sidc.be/SILSO/INFO/snmtotcsv.php"
LICENSE = "Public domain (SILSO / WDC-SILSO, Royal Observatory of Belgium)"
REFERENCE = "SILSO World Data Center — monthly mean total sunspot number (Clette & Lefevre)"
MAX_BYTES = 5 * 1024 * 1024


def download_sunspots(dest: str | Path, *, authorized: bool, url: str = URL) -> dict[str, Any]:
    if not authorized:
        raise PermissionError("Downloading external data requires authorized=True (policy).")
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 - fixed https host
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("download exceeds cap")
    dest.write_bytes(data)
    return {"path": str(dest), "bytes": len(data), "sha256": hash_file(dest),
            "url": url, "license": LICENSE, "reference": REFERENCE,
            "downloaded_at": now_iso()}


def _parse(text: str) -> tuple[np.ndarray, np.ndarray, int]:
    times, values = [], []
    missing = 0
    for line in text.splitlines():
        parts = line.replace(",", ".").split(";")
        if len(parts) < 4:
            continue
        try:
            dec_year = float(parts[2])
            ssn = float(parts[3])
        except ValueError:
            continue
        if ssn < 0:  # SILSO missing marker
            missing += 1
            continue
        times.append(dec_year)
        values.append(ssn)
    return np.array(times), np.array(values), missing


def analyze_sunspots(csv_path: str | Path, *, manifest: dict[str, Any] | None = None
                     ) -> dict[str, Any]:
    text = Path(csv_path).read_text(encoding="utf-8", errors="replace")
    t, y, missing = _parse(text)
    if len(y) < 120:
        raise ValueError("sunspot series too short")
    manifest = manifest or {"sha256": hash_text(text), "license": LICENSE, "reference": REFERENCE}

    dt = float(np.median(np.diff(t)))  # ~1/12 year
    yc = y - y.mean()
    # FFT periodicity (dominant period in years).
    freqs = np.fft.rfftfreq(len(yc), d=dt)
    power = np.abs(np.fft.rfft(yc)) ** 2
    power[0] = 0.0
    peak = int(np.argmax(power))
    dominant_period = float(1.0 / freqs[peak]) if freqs[peak] > 0 else float("inf")

    # Cycle-length variability via peak-to-peak spacing of a smoothed series ->
    # periodic vs quasiperiodic.
    win = max(13, int(1.0 / dt))
    kernel = np.ones(win) / win
    smooth = np.convolve(y, kernel, mode="same")
    peaks = [i for i in range(win, len(smooth) - win)
             if smooth[i] == max(smooth[i - win:i + win])]
    peak_years = t[peaks] if peaks else np.array([])
    cycle_lengths = np.diff(peak_years) if len(peak_years) > 1 else np.array([])
    cycle_mean = float(np.mean(cycle_lengths)) if len(cycle_lengths) else 0.0
    cycle_std = float(np.std(cycle_lengths)) if len(cycle_lengths) else 0.0
    quasiperiodic = bool(cycle_std > 0.1 * cycle_mean) if cycle_mean else False

    # Low-activity regime (Dalton-minimum-like): a multi-decade stretch below a threshold.
    decade_mean = {}
    for start in range(int(t.min()), int(t.max()), 10):
        mask = (t >= start) & (t < start + 10)
        if mask.sum() > 12:
            decade_mean[start] = float(np.mean(y[mask]))
    overall = float(np.mean(y))
    low_regimes = [d for d, m in decade_mean.items() if m < 0.5 * overall]

    return {
        "n": len(y), "missing_months": missing,
        "time_span_years": [round(float(t.min()), 1), round(float(t.max()), 1)],
        "manifest": {"sha256": manifest.get("sha256"), "license": manifest.get("license"),
                     "reference": manifest.get("reference")},
        "dominant_period_years": round(dominant_period, 2),
        "cycle_mean_years": round(cycle_mean, 2), "cycle_std_years": round(cycle_std, 2),
        "classification": "quasiperiodic" if quasiperiodic else "periodic",
        "low_activity_decades": low_regimes,
        "uncertainty_note": ("Cycle length varies (~9–14 yr); amplitude varies strongly. "
                             "This is quasi-periodicity, not a clean sinusoid."),
        "cannot_conclude": [
            "El mecanismo físico (dínamo solar) NO puede inferirse de esta serie.",
            "No se declaran ciclos futuros ni predicciones.",
            "El período dominante es una estimación con incertidumbre, no una ley.",
            "Los mínimos de actividad son regímenes observados, no explicados.",
        ],
    }
