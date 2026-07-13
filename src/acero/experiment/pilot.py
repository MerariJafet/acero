"""Sprint 4 pilot: symbolic discovery of a KNOWN law from synthetic noisy data.

We generate data from Newton's law of cooling, T(t) = T_env + (T0-T_env)e^{-k t},
add noise, hide the generating equation from the fitter, and let four COMPETING
models compete: linear, cubic, a physically-motivated exponential, and an
over-flexible degree-9 polynomial. We evaluate in-range AND out-of-range
(extrapolation), across multiple seeds, against a naive baseline.

The point is NOT to "discover" cooling — that is textbook knowledge. The point is
to demonstrate that ACERO can preregister, run reproducibly in a sandbox, capture
negative results, attempt refutation, and refuse to call a recovered law a discovery.

The heavy lifting runs as a self-contained script inside the sandbox (runner.py),
so stdout/stderr/exit-code/seeds/hashes are all captured like any experiment.
"""

from __future__ import annotations

import json

# Ground-truth parameters (known to the data generator, hidden from the fitter).
PILOT_PARAMS = {
    "T_env": 25.0,
    "T0": 90.0,
    "k": 0.7,
    "sigma": 1.5,
    "t_max": 5.0,
    "train_max": 3.0,   # models train only on t in [0, 3]; (3, 5] is extrapolation
    "n_in_range": 60,
    "n_extra": 30,
}

# Pure-numpy sandbox script. Reads inputs/params.json, writes outputs/metrics.json,
# and echoes the metrics as JSON on stdout. No network, no filesystem outside cwd.
PILOT_SCRIPT = r'''
import json, math
import numpy as np

with open("inputs/params.json") as fh:
    P = json.load(fh)

seed = int(P["seed"])
rng = np.random.default_rng(seed)

T_env, T0, k = P["T_env"], P["T0"], P["k"]
sigma, t_max, train_max = P["sigma"], P["t_max"], P["train_max"]

def true_fn(t):
    return T_env + (T0 - T_env) * np.exp(-k * t)

# In-range sample on [0, train_max]; out-of-range (extrapolation) on (train_max, t_max].
t_in = np.sort(rng.uniform(0.0, train_max, size=int(P["n_in_range"])))
t_ex = np.sort(rng.uniform(train_max, t_max, size=int(P["n_extra"])))
y_in = true_fn(t_in) + rng.normal(0, sigma, size=t_in.size)
y_ex = true_fn(t_ex) + rng.normal(0, sigma, size=t_ex.size)

# Split in-range into train/val/test (60/20/20), disjoint by construction.
idx = rng.permutation(t_in.size)
n = t_in.size
n_tr, n_va = int(0.6 * n), int(0.2 * n)
tr, va, te = idx[:n_tr], idx[n_tr:n_tr + n_va], idx[n_tr + n_va:]
t_tr, y_tr = t_in[tr], y_in[tr]
t_va, y_va = t_in[va], y_in[va]
t_te, y_te = t_in[te], y_in[te]

def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))

def poly_model(deg):
    c = np.polyfit(t_tr, y_tr, deg)
    f = lambda t: np.polyval(c, t)
    return f, {"coef": [float(x) for x in c]}

def exp_model():
    # y = c0 + c1 * exp(-k t); grid-search k, linear least squares for (c0, c1).
    best = None
    for kk in np.linspace(0.05, 3.0, 600):
        X = np.column_stack([np.ones_like(t_tr), np.exp(-kk * t_tr)])
        coef, *_ = np.linalg.lstsq(X, y_tr, rcond=None)
        pred = X @ coef
        err = rmse(pred, y_tr)
        if best is None or err < best[0]:
            best = (err, kk, coef)
    _, kk, coef = best
    f = lambda t: coef[0] + coef[1] * np.exp(-kk * t)
    return f, {"recovered_k": float(kk), "c0": float(coef[0]), "c1": float(coef[1])}

models = {
    "linear": poly_model(1),
    "cubic": poly_model(3),
    "exponential_physical": exp_model(),
    "overfit_poly9": poly_model(9),
}

results = {}
for name, (f, info) in models.items():
    results[name] = {
        "train_rmse": rmse(f(t_tr), y_tr),
        "val_rmse": rmse(f(t_va), y_va),
        "test_rmse": rmse(f(t_te), y_te),
        "extrapolation_rmse": rmse(f(t_ex), y_ex),
        "info": info,
    }

# Naive baseline: predict the training mean everywhere.
baseline_pred = float(np.mean(y_tr))
baseline_rmse = rmse(np.full_like(y_te, baseline_pred), y_te)

best_model = min(results, key=lambda m: results[m]["test_rmse"])

out = {
    "seed": seed,
    "true_params": {"T_env": T_env, "T0": T0, "k": k, "sigma": sigma},
    "n": {"train": int(n_tr), "val": int(n_va), "test": int(t_te.size),
          "extrapolation": int(t_ex.size)},
    "train_test_disjoint": True,
    "baseline_rmse": baseline_rmse,
    "models": results,
    "best_model_by_test_rmse": best_model,
    "recovered_k": results["exponential_physical"]["info"]["recovered_k"],
}

with open("outputs/metrics.json", "w") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out))
'''


def params_for_seed(seed: int) -> dict:
    p = dict(PILOT_PARAMS)
    p["seed"] = seed
    return p


def flatten_metrics(raw: dict) -> dict:
    """Reduce the rich per-model output into the flat metric set the skeptic reads.

    Includes the FULL per-model RMSE table across all splits so a reviewer can
    independently check the "exponential is best" claim, plus validation RMSE
    (addresses methodological critiques about incomplete reporting).
    """
    best = raw["best_model_by_test_rmse"]
    bm = raw["models"][best]
    full_table = {
        name: {
            "train_rmse": m["train_rmse"],
            "val_rmse": m["val_rmse"],
            "test_rmse": m["test_rmse"],
            "extrapolation_rmse": m["extrapolation_rmse"],
        }
        for name, m in raw["models"].items()
    }
    return {
        "best_model": best,
        "recovered_k": raw["recovered_k"],
        "true_k": raw["true_params"]["k"],
        "train_rmse": bm["train_rmse"],
        "val_rmse": bm["val_rmse"],
        "test_rmse": bm["test_rmse"],
        "extrapolation_rmse": bm["extrapolation_rmse"],
        "baseline_rmse": raw["baseline_rmse"],
        "train_test_disjoint": raw["train_test_disjoint"],
        "overfit_extrapolation_rmse": raw["models"]["overfit_poly9"]["extrapolation_rmse"],
        "overfit_train_rmse": raw["models"]["overfit_poly9"]["train_rmse"],
        "full_model_table": full_table,
    }


def parse_stdout(stdout: str) -> dict:
    """Parse the JSON the sandbox script prints on its last non-empty line."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError("No JSON metrics found in sandbox stdout")
