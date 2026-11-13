"""S5 parameter search: random search and ParEGO (Knowles, 2006) with a fitted GP.

Both methods share the first N_INITIAL uniform samples for a given seed, so
the comparison isolates the effect of the guided phase.
"""
from __future__ import annotations
import warnings
import numpy as np
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.exceptions import ConvergenceWarning

from . import controllers as C, evaluate as E
from .metrics import KEYS

DIM = 9
N_INITIAL, N_TOTAL = 20, 80
POOL_UNIFORM, POOL_LOCAL, LOCAL_SIGMA = 2000, 400, 0.08
RHO = 0.05  # augmented Chebyshev coefficient (ParEGO default)


def _evaluate(inp, u, cal_imp, bounds):
    p = C.s5_decode(u, cal_imp)
    m = E.score_calibration(inp, C.s5_score_policy(inp, p, bounds))
    return p, m


def _parego_next(U, Y, rng, seed):
    lo, hi = Y.min(0), Y.max(0)
    Yn = (Y - lo) / np.where(hi - lo > 0, hi - lo, 1.0)
    lam = rng.dirichlet(np.ones(Y.shape[1]))
    f = np.max(lam * Yn, axis=1) + RHO * np.sum(lam * Yn, axis=1)
    kernel = (ConstantKernel(1.0, (1e-3, 1e3))
              * Matern(length_scale=np.full(DIM, 0.5), length_scale_bounds=(1e-2, 1e2), nu=2.5)
              + WhiteKernel(1e-4, (1e-8, 1e-1)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=2,
                                  random_state=int(rng.integers(1 << 31)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        gp.fit(U, f)
    best = U[np.argsort(f)[:5]]
    local = np.clip(best[rng.integers(0, len(best), POOL_LOCAL)]
                    + rng.normal(0, LOCAL_SIGMA, (POOL_LOCAL, DIM)), 0, 1)
    pool = np.vstack([rng.uniform(size=(POOL_UNIFORM, DIM)), local])
    mu, sd = gp.predict(pool, return_std=True)
    sd = np.maximum(sd, 1e-9)
    imp = f.min() - mu
    z = imp / sd
    ei = imp * norm.cdf(z) + sd * norm.pdf(z)
    return pool[int(np.argmax(ei))], gp.kernel_


def run(inp, cal_imp, bounds, method: str, seed: int, n_total=N_TOTAL, n_initial=N_INITIAL):
    rng = np.random.default_rng(seed)
    U = list(rng.uniform(size=(n_initial, DIM)))      # shared initial design
    rows = []
    for i in range(n_total):
        if i < n_initial:
            u = U[i]; phase = "initial"
        elif method == "random":
            u = rng.uniform(size=DIM); U.append(u); phase = "random"
        else:
            Y = np.array([[r[k] for k in KEYS] for r in rows])
            u, _ = _parego_next(np.array(U[: len(rows)]), Y, rng, seed); U.append(u); phase = "guided"
        p, m = _evaluate(inp, u, cal_imp, bounds)
        rows.append({"method": method, "seed": seed, "evaluation": i, "search_phase": phase,
                     **{f"u{j}": float(v) for j, v in enumerate(u)}, **p, **m})
    return rows
