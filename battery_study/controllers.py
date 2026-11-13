"""Rule-based controllers S1-S5. None of them contains an end-of-horizon override:
the periodic SOC boundary makes such rules unnecessary."""
from __future__ import annotations
import numpy as np


def s1_pv_priority(inp):
    """Charge only from PV surplus; discharge to meet any deficit."""
    return lambda t, soc, cap, net: -net


def s2_peak_shaving(inp, target_kw, reserve_fraction, ceiling_kw, charge_hours):
    hours = set(int(h) for h in charge_hours); hour = inp.hour

    def policy(t, soc, cap, net):
        if net < 0:
            return -net
        if hour[t] in hours and soc < reserve_fraction * cap and net < ceiling_kw:
            return min(reserve_fraction * cap - soc, ceiling_kw - net)  # pre-peak reserve
        if net > target_kw:
            return -(net - target_kw)                                    # shave toward target
        if soc > reserve_fraction * cap:
            return -min(net, soc - reserve_fraction * cap)               # use energy above reserve
        return 0.0
    return policy


def _threshold_policy(signal, low, high, max_soc, ceiling_kw):
    def policy(t, soc, cap, net):
        if net < 0:
            return -net
        s = signal[t]
        if s <= low and soc < max_soc * cap and net < ceiling_kw:
            return min(max_soc * cap - soc, ceiling_kw - net)
        if s >= high:
            return -net
        return 0.0
    return policy


def s3_price_response(inp, low, high, max_soc, ceiling_kw):
    return _threshold_policy(inp.price, low, high, max_soc, ceiling_kw)


def s4_carbon_response(inp, low, high, max_soc, ceiling_kw):
    return _threshold_policy(inp.carbon, low, high, max_soc, ceiling_kw)


S5_NAMES = ("w_price", "w_carbon", "w_peak", "target_quantile", "reserve_fraction",
            "max_grid_charge_soc", "charge_score", "discharge_score", "ceiling_fraction")


def s5_decode(u, cal_import):
    """Map u in [0,1]^9 to controller parameters.

    Changes from the interim version: the target quantile range is widened to
    0.75-0.995, and the grid-charging ceiling is linear in kW (0 to the
    calibration P90 import) instead of a quantile in 0.2-0.6, whose lower part
    collapsed to 0 kW (about a quarter of that dimension disabled grid charging).
    """
    u = np.asarray(u, float)
    w = np.maximum(u[:3], 0.03); w = w / w.sum()
    charge = 0.08 + 0.35 * u[6]
    discharge = charge + 0.18 + 0.28 * u[7]
    tq = 0.75 + 0.245 * u[3]
    p90 = float(cal_import.quantile(0.90))
    return dict(w_price=float(w[0]), w_carbon=float(w[1]), w_peak=float(w[2]),
                target_quantile=float(tq), reserve_fraction=float(0.10 + 0.65 * u[4]),
                max_grid_charge_soc=float(0.45 + 0.50 * u[5]), charge_score=float(charge),
                discharge_score=float(discharge), ceiling_fraction=float(u[8]),
                target_kw=float(cal_import.quantile(tq)), charge_ceiling_kw=float(u[8] * p90))


def s5_score_policy(inp, p, bounds):
    price_lo, price_hi, carbon_lo, carbon_hi, import_hi = bounds
    zp = np.clip((inp.price - price_lo) / (price_hi - price_lo), 0, 1)
    zc = np.clip((inp.carbon - carbon_lo) / (carbon_hi - carbon_lo), 0, 1)
    wp, wc, wk = p["w_price"], p["w_carbon"], p["w_peak"]
    tgt, res, mx = p["target_kw"], p["reserve_fraction"], p["max_grid_charge_soc"]
    cs, ds, ceil = p["charge_score"], p["discharge_score"], p["charge_ceiling_kw"]

    def policy(t, soc, cap, net):
        if net < 0:
            return -net
        score = wp * zp[t] + wc * zc[t] + wk * min(max(net / import_hi, 0.0), 1.0)
        if net > tgt:
            return -(net - tgt)
        if score >= ds and soc > res * cap:
            return -min(net, soc - res * cap)
        if score <= cs and soc < mx * cap and net < ceil:
            return min(mx * cap - soc, ceil - net)
        return 0.0
    return policy


def s5_bounds(inp, cal_import):
    from . import config
    a, b = config.CALIBRATION
    return (float(inp.price[a:b].min()), float(inp.price[a:b].max()),
            float(inp.carbon[a:b].min()), float(inp.carbon[a:b].max()),
            float(cal_import.quantile(0.995)))
