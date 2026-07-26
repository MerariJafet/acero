"""Run a STRESS batch of recovery controls (may span domains) end-to-end, score it, and
LEARN per domain (record retro + auto-tune within the specificity floor). argv[1]=batch."""
import json
import sys
import time

from acero.discovery.store import DiscoveryStore
from acero.ledger.db import default_session_factory
from acero.ledger.service import ResearchLedger
from acero.portal.calibration import Calibration
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.missions import MissionEngine
from acero.portal.recovery_bench import controls_in_batch, learn, score_project
from acero.portal.workspace import WorkspaceService

BATCH = sys.argv[1] if len(sys.argv) > 1 else "s1"
BASE = "research/selfimprove"
LOG, OUT = f"{BASE}/stress_{BATCH}.log", f"{BASE}/stress_{BATCH}_results.json"


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


sf = default_session_factory()
_ = DiscoveryStore(sf, ResearchLedger(sf))
ws, hs, fl, eng = (WorkspaceService(sf), HypothesisService(sf),
                   HypothesisFlow(sf), MissionEngine(sf))
controls = controls_in_batch(BATCH)
log(f"=== stress batch {BATCH}: {len(controls)} controles ===")
projects = {}
for c in controls:
    try:
        p = ws.create_project(f"[control] {c['id']}", domain=c["domain"], topic=c["question"])
        pid = p["id"]
        hyps = hs.generate(pid, use_ai=True).get("created", [])
        if not hyps:
            log(f"{c['id']}: sin hipótesis, skip")
            continue
        fl.set_status(pid, hyps[0]["id"], "APPROVED", f"control {c['id']}")
        r = eng.start(pid, hyps[0]["id"], use_ai=True, sync=False, force=True)
        mids = [r["mission_id"]] if r.get("ok") else []
        projects[c["id"]] = {"pid": pid, "expected": c["expected"],
                             "domain": c["domain"], "mids": mids}
        log(f"{c['id']} [{c['domain']}]: {pid[:12]} · {len(hyps)} hyps · {len(mids)} misión")
    except Exception as e:  # noqa: BLE001
        log(f"{c['id']}: ERROR setup {repr(e)[:150]}")

log("=== esperando misiones ===")
deadline = time.time() + 7200
while time.time() < deadline:
    pend = sum(1 for info in projects.values() for m in eng.list_missions(info["pid"])
               if m.get("id") in info["mids"] and m.get("status") in ("PENDING", "RUNNING"))
    if pend == 0:
        break
    log(f"pendientes: {pend}")
    time.sleep(45)

by_domain: dict = {}
results = []
for cid, info in projects.items():
    try:
        s = score_project(info["pid"], info["expected"], sf)
        s["control"] = cid
        results.append(s)
        by_domain.setdefault(info["domain"], []).append(s)
        log(f"{cid} [{info['domain']}]: esp={s['expected']} out={s['outcome']} correct={s['correct']}")
    except Exception as e:  # noqa: BLE001
        log(f"{cid}: ERROR score {repr(e)[:120]}")

learned = {}
for domain, res in by_domain.items():
    lr = learn(domain, res)
    learned[domain] = lr
    d = lr["decision"]
    log(f"APRENDIZAJE {domain}: {lr['summary']} → {d['action']} {d.get('before')}→{d.get('after')}")

json.dump({"batch": BATCH, "results": results, "learned": learned,
           "retro": Calibration().retro()}, open(OUT, "w"), ensure_ascii=False, indent=2)
log("=== FIN ===")
sys.exit(0)
