"""The sandbox script for the Hidden Dynamics benchmark (runs isolated, numpy-only).

Reads inputs/params.json: {system, seed, noise, train_max, t_max, n_in, n_extra}.
Generates data from a HIDDEN dynamical system, fits several competing model families,
and reports RMSE across train/val/test/extrapolation plus a coarse behavior label per
model in the extrapolation region (for discrimination). Writes outputs/metrics.json
and prints the JSON on stdout.

Systems: exponential_decay | damped_oscillator | logistic | predator_prey | chaotic_map.
"""

BENCH_SCRIPT = r'''
import json, math
import numpy as np

with open("inputs/params.json") as fh:
    P = json.load(fh)

system = P["system"]
seed = int(P["seed"])
noise = float(P["noise"])
train_max = float(P.get("train_max", 3.0))
t_max = float(P.get("t_max", 5.0))
n_in = int(P.get("n_in", 60))
n_extra = int(P.get("n_extra", 30))
rng = np.random.default_rng(seed)

def gen(t):
    if system == "exponential_decay":
        return 25.0 + (90.0 - 25.0) * np.exp(-0.7 * t)
    if system == "damped_oscillator":
        return 5.0 * np.exp(-0.4 * t) * np.cos(2.5 * t)
    if system == "logistic":
        K, y0, r = 10.0, 0.5, 1.5
        return K / (1.0 + ((K - y0) / y0) * np.exp(-r * t))
    if system == "predator_prey":
        # Lotka-Volterra prey series via Euler; smooth downsample onto t.
        a, b, c, d = 1.1, 0.4, 0.4, 0.1
        dt = 0.01
        steps = int(t_max / dt) + 2
        x, y = 10.0, 5.0
        xs = []
        for i in range(steps):
            xs.append(x)
            dx = a * x - b * x * y
            dy = -c * y + d * x * y
            x += dx * dt; y += dy * dt
        idx = np.clip((t / dt).astype(int), 0, steps - 1)
        return np.array(xs)[idx]
    if system == "chaotic_map":
        r = 3.9
        n = int(t_max) + 2
        seq = [0.5]
        for _ in range(n):
            seq.append(r * seq[-1] * (1 - seq[-1]))
        idx = np.clip(t.astype(int), 0, n)
        return np.array(seq)[idx]
    raise ValueError("unknown system")

t_in = np.sort(rng.uniform(0.0, train_max, size=n_in))
t_ex = np.sort(rng.uniform(train_max, t_max, size=n_extra))
y_in = gen(t_in) + rng.normal(0, noise, size=t_in.size)
y_ex = gen(t_ex) + rng.normal(0, noise, size=t_ex.size)

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
    return lambda t: np.polyval(c, t)

def exp_model():
    best = None
    for kk in np.linspace(0.05, 3.0, 400):
        X = np.column_stack([np.ones_like(t_tr), np.exp(-kk * t_tr)])
        coef, *_ = np.linalg.lstsq(X, y_tr, rcond=None)
        err = rmse(X @ coef, y_tr)
        if best is None or err < best[0]:
            best = (err, kk, coef)
    _, kk, coef = best
    return lambda t: coef[0] + coef[1] * np.exp(-kk * t)

def damped_model():
    best = None
    for g in np.linspace(0.05, 1.5, 40):
        for w in np.linspace(0.5, 4.0, 60):
            X = np.column_stack([np.exp(-g * t_tr) * np.cos(w * t_tr),
                                 np.exp(-g * t_tr) * np.sin(w * t_tr)])
            coef, *_ = np.linalg.lstsq(X, y_tr, rcond=None)
            err = rmse(X @ coef, y_tr)
            if best is None or err < best[0]:
                best = (err, g, w, coef)
    _, g, w, coef = best
    return lambda t: coef[0] * np.exp(-g * t) * np.cos(w * t) + coef[1] * np.exp(-g * t) * np.sin(w * t)

def logistic_model():
    best = None
    for K in np.linspace(max(1e-3, y_tr.max() * 0.8), y_tr.max() * 1.5 + 1e-3, 25):
        for r in np.linspace(0.2, 3.0, 40):
            # linearise: y ~ K / (1 + A exp(-r t)); grid A too via least squares on transform
            with np.errstate(all="ignore"):
                z = np.clip(K / np.clip(y_tr, 1e-6, None) - 1.0, 1e-6, None)
                logz = np.log(z)
            X = np.column_stack([np.ones_like(t_tr), -t_tr])
            coef, *_ = np.linalg.lstsq(X, logz, rcond=None)
            A = math.exp(coef[0]); rr = coef[1]
            pred = K / (1.0 + A * np.exp(-rr * t_tr))
            err = rmse(pred, y_tr)
            if best is None or (np.isfinite(err) and err < best[0]):
                best = (err, K, A, rr)
    _, K, A, rr = best
    return lambda t: K / (1.0 + A * np.exp(-rr * t))

models = {
    "mean": (lambda t: np.full_like(np.asarray(t, dtype=float), float(np.mean(y_tr)))),
    "linear": poly_model(1),
    "cubic": poly_model(3),
    "exponential": exp_model(),
    "poly9": poly_model(9),
}
if system in ("damped_oscillator",):
    models["damped"] = damped_model()
if system in ("logistic", "predator_prey"):
    models["logistic"] = logistic_model()

def behavior_label(f):
    ts = np.linspace(train_max, t_max, 40)
    ys = np.asarray(f(ts), dtype=float)
    if not np.all(np.isfinite(ys)):
        return "diverging"
    d = np.diff(ys)
    sign_changes = int(np.sum(np.diff(np.sign(d)) != 0))
    rng_amp = float(np.max(ys) - np.min(ys))
    if abs(ys[-1]) > 10 * (abs(ys[0]) + 1e-9):
        return "diverging"
    if sign_changes >= 2:
        return "oscillatory"
    if rng_amp < 0.05 * (abs(np.mean(ys)) + 1e-9):
        return "flat"
    if abs(d[-1]) < 0.2 * abs(d[0] + 1e-9):
        return "saturating"
    return "monotonic"

results = {}
labels = {}
for name, f in models.items():
    results[name] = {
        "train_rmse": rmse(f(t_tr), y_tr),
        "val_rmse": rmse(f(t_va), y_va),
        "test_rmse": rmse(f(t_te), y_te),
        "extrapolation_rmse": rmse(f(t_ex), y_ex),
    }
    labels[name] = behavior_label(f)

baseline_rmse = rmse(np.full_like(y_te, float(np.mean(y_tr))), y_te)
best_test = min(results, key=lambda m: results[m]["test_rmse"])
best_extra = min(results, key=lambda m: results[m]["extrapolation_rmse"])

out = {
    "system": system, "seed": seed, "noise": noise,
    "hidden_family": {"exponential_decay": "exponential", "damped_oscillator": "damped",
                      "logistic": "logistic", "predator_prey": "logistic",
                      "chaotic_map": "none"}.get(system, "unknown"),
    "n": {"train": int(n_tr), "val": int(n_va), "test": int(t_te.size), "extrapolation": int(t_ex.size)},
    "train_test_disjoint": True,
    "baseline_rmse": baseline_rmse,
    "models": results,
    "behavior_labels": labels,
    "best_model_by_test_rmse": best_test,
    "best_model_by_extrapolation_rmse": best_extra,
}
with open("outputs/metrics.json", "w") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out))
'''
