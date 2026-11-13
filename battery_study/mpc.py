"""Optimisation benchmarks.

1. Rolling-horizon MPC: every hour a 24-h linear programme is solved with a
   linearised battery (one-way efficiency sqrt(0.9), no power derating); only
   the first-hour request is applied to the CityLearn-equation simulator, so
   reported KPIs come from the same simulator as S1-S5.
2. Annual LP benchmark: the same linear model over the whole year with perfect
   foresight and a periodic SOC constraint. It omits simulator losses and
   derating and therefore supplies an optimistic model-based lower bound for
   the study's import-only objective under its dispatch boundary. Its solution
   is not claimed to be attainable in the nonlinear battery simulator.
"""
from __future__ import annotations
import numpy as np
from scipy import sparse
from scipy.optimize import linprog

ETA = 0.9 ** 0.5
H = 24


def _matrices(h, eta=ETA, periodic=False):
    I = sparse.identity(h, format="csr")
    Sh = sparse.eye(h, k=-1, format="csr")
    if periodic:
        Sh = Sh + sparse.csr_matrix(([1.0], ([0], [h - 1])), shape=(h, h))
    Z = sparse.csr_matrix((h, h)); z1 = sparse.csr_matrix((h, 1))
    # variables: c d s g x Pk ; s_t - s_{t-1} - eta c_t + d_t/eta = 0 ; g - x - c + d = net
    Aeq = sparse.vstack([sparse.hstack([-eta * I, I / eta, I - Sh, Z, Z, z1]),
                         sparse.hstack([-I, I, Z, I, -I, z1])]).tocsc()
    Aub = sparse.hstack([Z, Z, Z, I, Z, -np.ones((h, 1))]).tocsc()   # g_t <= Pk
    return Aeq, Aub


class RollingMPC:
    def __init__(self, inp, forecast="perfect", w_price=1.0, w_carbon=0.0, w_peak=0.0, horizon=H):
        self.inp, self.fc, self.h = inp, forecast, horizon
        self.wp, self.wc, self.wk = w_price, w_carbon, w_peak
        self.Aeq, self.Aub = _matrices(horizon)
        self.N = len(inp.net); self.failures = 0

    def _forecast(self, t):
        idx = (t + np.arange(self.h)) % self.N
        if self.fc == "perfect":
            n, c = self.inp.net[idx].copy(), self.inp.carbon[idx].copy()
        elif self.fc == "persistence":   # same hour of the previous day
            j = (idx - 24) % self.N
            n, c = self.inp.net[j].copy(), self.inp.carbon[j].copy()
            c[0] = self.inp.carbon[t]
        else:
            raise ValueError(self.fc)
        return n, c, self.inp.price[idx]   # tariff schedule is known in advance

    def __call__(self, t, soc, cap, net_now):
        h = self.h
        n, c, p = self._forecast(t); n[0] = net_now
        beq = np.r_[np.zeros(h), n]; beq[0] += soc
        cost = np.zeros(5 * h + 1)
        cost[3 * h:4 * h] = self.wp * p + self.wc * c
        cost[-1] = self.wk
        cost[:h] += 1e-6  # break ties against needless cycling
        bnd = ([(0, 5.0)] * h + [(0, 5.0)] * h + [(0, cap)] * h + [(0, None)] * h
               + [(0, max(-v, 0.0)) for v in n] + [(0, None)])   # export only from PV surplus
        r = linprog(cost, A_ub=self.Aub, b_ub=np.zeros(h), A_eq=self.Aeq, b_eq=beq,
                    bounds=bnd, method="highs")
        if not r.success:
            self.failures += 1
            return -net_now
        return float(r.x[0] - r.x[h])


def annual_bound(inp, objective="cost", peak_cap=None, capacity=6.4, power=5.0):
    T = len(inp.net)
    Aeq, Aub = _matrices(T, periodic=True)
    c = np.zeros(5 * T + 1)
    if objective == "cost":
        c[3 * T:4 * T] = inp.price
    elif objective == "carbon":
        c[3 * T:4 * T] = inp.carbon
    elif objective == "peak":
        c[-1] = 1.0; c[3 * T:4 * T] = 1e-5 * inp.price
    bnd = ([(0, power)] * T + [(0, power)] * T + [(0, capacity)] * T + [(0, None)] * T
           + [(0, max(-v, 0.0)) for v in inp.net] + [(0, peak_cap)])
    r = linprog(c, A_ub=Aub, b_ub=np.zeros(T), A_eq=Aeq, b_eq=np.r_[np.zeros(T), inp.net],
                bounds=bnd, method="highs")
    assert r.success, r.message
    g = r.x[3 * T:4 * T]
    return {"electricity_cost_currency": float(g @ inp.price), "carbon_emissions_kgco2": float(g @ inp.carbon),
            "peak_grid_import_kw": float(g.max()), "grid_import_kwh": float(g.sum()),
            "grid_export_kwh": float(r.x[4 * T:5 * T].sum())}
