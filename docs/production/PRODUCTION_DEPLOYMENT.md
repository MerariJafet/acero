# ACERO Production Deployment — Verified Infrastructure & Blocker

Date: 2026-07-18. All facts below were **verified live**, not assumed.

## Verified infrastructure (FASE 0 recon)

| Item | Verified value |
|------|----------------|
| Domain | **merari-acero.com** — DNS → 34.66.145.8, HTTPS 200 (live) |
| VM | GCP `vm-merari-landing`, Ubuntu 22.04, SSH as `merari` (works) |
| Resources | **2 vCPU, 958 MB RAM (~274 MB free), 20 GB disk (1.4 GB free, 93% used)** |
| Runtime | Python **3.10.12**, **no Docker**, PM2 process manager, Nginx + Certbot |
| Running services | merari-landing (Next:3000), kronos-api (8768), kronos-dashboard (streamlit:8501), nexus-api (8000), postgres:5432, redis:6379 |
| Deploy flow | `git push production` → bare repo `ssh://merari@34.66.145.8/home/merari/repo/merari-landing.git` → post-receive build/PM2 |
| nginx routing | `/` → landing:3000; `/kronos/` → 8501; `/nexus/`, `/api/` → 8000; `/kronos-api/` → 8768; HTTPS via Certbot |
| Landing stack | Next.js 16 + React 19 + Tailwind + Three.js; nav pattern for KRONOS/NEXUS entry points exists |

## The blocker (honest)

ACERO requires **Python 3.12** and a heavy scientific stack (numpy, scipy,
astropy, scikit-learn, pandas). Installing that stack needs **~0.5–1 GB disk** and
its processes (FastAPI + multiprocess workers + astropy) need **well over the
~274 MB RAM free**. The VM is at **93% disk and has ~274 MB RAM free** while
already serving three live products.

**Conclusion:** deploying full ACERO to this exact VM is **not safely feasible**
and would risk destabilising the live merari-acero.com / Kronos / Nexus services.
This is a genuine capacity limit, not a code gap.

## Options (a human/cost decision — `BLOCKED_BY_HUMAN_DECISION`)

| Option | What | Trade-off |
|--------|------|-----------|
| **1. Upgrade the VM** | resize to ≥2 GB RAM + more disk, install Python 3.12 | **cost**; cleanest path to a real full-ACERO deploy |
| **2. Separate small VM/host for ACERO** | ACERO on its own host; nginx on the landing reverse-proxies `acero.merari-acero.com` | **cost**; best isolation (own resources, own restart) |
| **3. Slim read-only portal** | deploy only the portal shell + pre-computed results, science runs offline | fits tighter, but ACERO imports pull scipy/astropy widely — real slimming effort, and disk still tight |
| **4. Hold deployment** | keep ACERO local; add an honest "Investigación ACERO" landing page describing the platform + status, not a live app | zero cost; the button would lead to an info page, not a running portal (must be labelled honestly, not "disponible") |

## Recommended entry-point architecture (once a runtime exists)

Subdomain **`acero.merari-acero.com`** with its own Certbot cert and an nginx
`proxy_pass` to the ACERO service port — mirrors the existing `/kronos/` `/nexus/`
pattern, gives cookie/session isolation from the landing, and keeps the strict
portal CSP intact. Documented as the decision in the button ADR when built.

## What is NOT done (and will not be faked)
- No deployment performed (blocked as above). The score reflects this honestly.
- The landing has **not** been modified; no button pushed to production yet —
  pending the Option decision, because a button must lead to a real, reachable
  target (never a dead link, never "disponible" for an unproven URL).
