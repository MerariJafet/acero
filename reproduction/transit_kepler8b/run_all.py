"""Standalone driver: download -> analyze (3 methods) -> compare to expected.

No ACERO imports. Prints a JSON report and exits non-zero on failure to reproduce.
"""

from __future__ import annotations

import json
from pathlib import Path

from analyze import analyze
from download_data import download_all

HERE = Path(__file__).parent


def main() -> int:
    data_dir = HERE / "_data"
    hashes = download_all(data_dir)

    manifest_path = HERE / "data_manifests.json"
    hash_drift: list[str] = []
    if manifest_path.exists():
        recorded = {m["source_url"].split("/")[-1]: m["sha256"]
                    for m in json.loads(manifest_path.read_text())["manifests"]}
        for name, h in hashes.items():
            if name in recorded and recorded[name] != h:
                hash_drift.append(name)

    result = analyze(data_dir)
    expected = json.loads((HERE / "expected_outputs.json").read_text())
    within = abs(result["method_A_BLS"] - expected["expected_period_days"]) \
        <= expected["tolerance_days"]

    report = {
        "reproduction_state": "INDEPENDENT_PROCESS_REPRODUCTION",
        "note": "NOT external scientific replication.",
        "hash_drift": hash_drift, "no_hash_drift": len(hash_drift) == 0,
        "analysis": result,
        "matches_expected": bool(within),
        "reproduced": bool(within and result["all_recover_known"] and not hash_drift),
        "is_discovery": False,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
