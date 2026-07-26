"""Self-improvement driver (what a cron / claude CLI would call):
run the recovery benchmark for ONE domain, score it, and LEARN (record retro +
auto-tune within guardrails). Domain passed as argv[1]. Safe: it only tunes bounded
parameters and never crosses the specificity floor (see calibration.py)."""
import json
import sys
import time

from acero.ledger.db import default_session_factory
from acero.portal.calibration import Calibration
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.missions import MissionEngine
from acero.portal.recovery_bench import controls_for, learn, score_project
from acero.portal.workspace import WorkspaceService

DOMAIN = sys.argv[1] if len(sys.argv) > 1 else "chemistry"
BASE = "research/selfimprove"
LOG = f"{BASE}/gen_{DOMAIN}.log"
OUT = f"{BASE}/gen_{DOMAIN}_results.json"


def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


sf = default_session_factory()
ws, hs, fl, eng = WorkspaceService(sf), HypothesisService(sf), HypothesisFlow(sf), MissionEngine(sf)
controls = controls_for(DOMAIN)
log(f"=== generalización: dominio={DOMAIN}, {len(controls)} controles ===")
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
        r = eng.start(pid, hyps[0]["id"], use_ai=True, sync=False, force=True)  # controls skip the gate
        mids = [r["mission_id"]] if r.get("ok") else []
        projects[c["id"]] = {"pid": pid, "expected": c["expected"], "mids": mids}
        log(f"{c['id']}: {pid[:12]} · {len(hyps)} hyps · {len(mids)} misión")
    except Exception as e:  # noqa: BLE001
        log(f"{c['id']}: ERROR setup {repr(e)[:150]}")

log("=== esperando misiones ===")
deadline = time.time() + 5400
while time.time() < deadline:
    pend = sum(1 for info in projects.values() for m in eng.list_missions(info["pid"])
               if m.get("id") in info["mids"] and m.get("status") in ("PENDING", "RUNNING"))
    if pend == 0:
        break
    log(f"pendientes: {pend}")
    time.sleep(45)

results = []
for cid, info in projects.items():
    try:
        s = score_project(info["pid"], info["expected"], sf)
        s["control"] = cid
        results.append(s)
        log(f"{cid}: esp={s['expected']} out={s['outcome']} correct={s['correct']}")
    except Exception as e:  # noqa: BLE001
        log(f"{cid}: ERROR score {repr(e)[:120]}")

# LEARN: record retro + auto-tune within guardrails
lr = learn(DOMAIN, results)
log(f"=== APRENDIZAJE {DOMAIN}: {lr['summary']} ===")
log(f"=== decisión: {lr['decision']['action']} {lr['decision'].get('before')}→{lr['decision'].get('after')} | {lr['decision']['reason'][:100]} ===")
json.dump({"domain": DOMAIN, "results": results, "learn": lr,
           "retro": Calibration().retro(DOMAIN)}, open(OUT, "w"), ensure_ascii=False, indent=2)
log("=== FIN ===")
sys.exit(0)
