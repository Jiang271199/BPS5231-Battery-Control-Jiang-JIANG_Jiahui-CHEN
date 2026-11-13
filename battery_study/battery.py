"""Hourly battery simulator reproducing the CityLearn v1.3.6 Battery/StorageDevice equations.

This is a speed-optimised, numerically identical re-implementation of
`run_battery_controller` in 07_pv_priority_battery.py (verified in
tests/test_battery.py). Two additions:
  * `initial_soc` and arbitrary step windows;
  * `simulate_periodic`, which iterates the initial SOC until it equals the
    final SOC (cyclic boundary), removing end-of-horizon artefacts.

Controller interface: policy(t, soc, capacity, net) -> requested AC energy
(kWh, + charge / - discharge) for absolute source step t.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config

POWER_EFF = ((0.0, 0.83), (0.3, 0.83), (0.7, 0.90), (0.8, 0.90), (1.0, 0.85))
CAP_POWER = ((0.0, 1.0), (0.8, 1.0), (1.0, 0.2))


def _interp(x, curve):
    # CityLearn v1.3.6 convention: index = max(0, argmax(x <= xs) - 1).
    idx = 0
    for i, (xi, _) in enumerate(curve):
        if x <= xi:
            idx = i
            break
    idx = max(0, idx - 1)
    x0, y0 = curve[idx]
    x1, y1 = curve[idx + 1]
    return y0 + (y1 - y0) / (x1 - x0) * (x - x0)


def simulate(inp, policy, start=0, stop=config.N_STEPS, initial_soc=0.0, record=True):
    b = inp.battery
    cap0 = float(b["capacity"]); pnom = float(b["nominal_power"])
    loss = float(b.get("loss_coefficient", 0.006))
    closs = float(b.get("capacity_loss_coefficient", 1.0e-5))
    n = stop - start
    soc = float(initial_soc); cap = cap0
    out = {k: np.empty(n) for k in ("request", "exchange", "soc_start", "soc_end", "cap_start",
                                    "cap_end", "max_power", "eff", "loss")}
    net = inp.net
    for i in range(n):
        t = start + i
        base = net[t]
        req = float(policy(t, soc, cap, base))
        s0 = soc; c0 = cap
        s_sb = s0 * (1.0 - loss)
        frac = s_sb / c0 if c0 > 0 else 0.0
        pmax = pnom * _interp(frac, CAP_POWER)
        pl = min(req, pmax) if req >= 0.0 else max(req, -pmax)
        eff = _interp(abs(pl) / pnom, POWER_EFF) ** 0.5
        if pl >= 0.0:
            soc = min(s_sb + pl * eff, c0)
        else:
            soc = max(0.0, s_sb + pl / eff)
        d = soc - s_sb
        ex = d / eff if d >= 0.0 else d * eff
        cap = c0 - (closs * cap0 * abs(ex) / (2.0 * c0) if c0 > 0 else 0.0)
        o = out
        o["request"][i] = req; o["exchange"][i] = ex; o["soc_start"][i] = s0; o["soc_end"][i] = soc
        o["cap_start"][i] = c0; o["cap_end"][i] = cap; o["max_power"][i] = pmax; o["eff"][i] = eff
        o["loss"][i] = max(ex, 0.0) - max(-ex, 0.0) - d
    return _frame(inp, start, stop, out) if record else out


def _frame(inp, start, stop, o):
    sl = slice(start, stop)
    strat = inp.net[sl] + o["exchange"]
    strat[np.abs(strat) < 1e-12] = 0.0
    imp = np.clip(strat, 0, None); exp = np.clip(-strat, 0, None)
    return pd.DataFrame({
        "timestamp": np.arange(start, stop), "month": inp.month[sl], "hour": inp.hour[sl],
        "load_kwh": inp.load[sl], "pv_kwh": inp.pv[sl], "price_per_kwh": inp.price[sl],
        "carbon_intensity_kg_per_kwh": inp.carbon[sl], "baseline_net_kwh": inp.net[sl],
        "control_request_kwh": o["request"], "battery_exchange_kwh": o["exchange"],
        "battery_charge_input_kwh": np.clip(o["exchange"], 0, None),
        "battery_discharge_output_kwh": np.clip(-o["exchange"], 0, None),
        "battery_loss_kwh": o["loss"], "one_way_efficiency": o["eff"],
        "max_battery_power_kw": o["max_power"], "soc_start_kwh": o["soc_start"],
        "soc_end_kwh": o["soc_end"], "capacity_start_kwh": o["cap_start"],
        "capacity_end_kwh": o["cap_end"], "strategy_net_kwh": strat,
        "grid_import_kwh": imp, "grid_export_kwh": exp,
        "hourly_cost": imp * inp.price[sl], "hourly_carbon_kg": imp * inp.carbon[sl],
    })


def simulate_periodic(inp, policy, start=0, stop=config.N_STEPS, initial_soc=0.0,
                      tol=config.PERIODIC_TOL_KWH, max_passes=config.PERIODIC_MAX_PASSES):
    """Fixed-point iteration on the initial SOC so that SOC(end) == SOC(start)."""
    if stop <= start:
        raise ValueError("The simulation window must contain at least one hour")
    if max_passes < 1:
        raise ValueError("max_passes must be positive")
    soc0 = float(initial_soc)
    for passes in range(1, max_passes + 1):
        o = simulate(inp, policy, start, stop, soc0, record=False)
        residual = abs(float(o["soc_end"][-1]) - soc0)
        if residual <= tol:
            break
        soc0 = float(o["soc_end"][-1])
    else:
        raise RuntimeError(
            f"Periodic SOC did not converge in {max_passes} passes "
            f"(residual {residual:.6g} kWh; tolerance {tol:.6g} kWh)"
        )
    frame = _frame(inp, start, stop, o)
    frame.attrs["periodic_residual_kwh"] = residual
    frame.attrs["periodic_passes"] = passes
    return frame
