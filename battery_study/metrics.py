"""KPI definitions. Cost and carbon count grid imports only (main case)."""
from __future__ import annotations
import numpy as np
import pandas as pd

KEYS = ("electricity_cost_currency", "carbon_emissions_kgco2", "peak_grid_import_kw")


def kpis(x: pd.DataFrame, capacity_kwh: float = 6.4) -> dict:
    imp = x["grid_import_kwh"].to_numpy(); exp = x["grid_export_kwh"].to_numpy()
    load = float(x["load_kwh"].sum()); pv = float(x["pv_kwh"].sum())
    if "battery_charge_input_kwh" in x:
        thr = float(x["battery_charge_input_kwh"].sum() + x["battery_discharge_output_kwh"].sum())
        soc0 = float(x["soc_start_kwh"].iloc[0]); soc1 = float(x["soc_end_kwh"].iloc[-1])
    else:
        thr = soc0 = soc1 = 0.0
    monthly_peaks = pd.Series(imp, index=x["month"].to_numpy()).groupby(level=0).max()
    return {
        "grid_import_kwh": float(imp.sum()),
        "grid_export_kwh": float(exp.sum()),
        "electricity_cost_currency": float(x["hourly_cost"].sum()),
        "carbon_emissions_kgco2": float(x["hourly_carbon_kg"].sum()),
        # Hourly energy over a 1 h step = hourly-average power (kW).
        "peak_grid_import_kw": float(imp.max()),
        "peak_step": int(x["timestamp"].iloc[int(imp.argmax())]),
        "mean_monthly_peak_kw": float(monthly_peaks.mean()),
        "top10_hours_mean_import_kw": float(np.sort(imp)[-10:].mean()),
        "p99_import_kw": float(np.quantile(imp, 0.99)),
        "battery_ac_throughput_kwh": thr,
        "equivalent_full_cycles": thr / (2.0 * capacity_kwh),
        "pv_self_consumption_fraction": float(1 - exp.sum() / pv) if pv > 0 else np.nan,
        "self_sufficiency_fraction": float(1 - imp.sum() / load),
        "soc_start_kwh": soc0, "soc_end_kwh": soc1,
    }


def no_battery_frame(inp, start=0, stop=8760) -> pd.DataFrame:
    sl = slice(start, stop); net = inp.net[sl]
    imp = np.clip(net, 0, None); exp = np.clip(-net, 0, None)
    return pd.DataFrame({"timestamp": np.arange(start, stop), "month": inp.month[sl],
                         "hour": inp.hour[sl], "load_kwh": inp.load[sl], "pv_kwh": inp.pv[sl],
                         "grid_import_kwh": imp, "grid_export_kwh": exp,
                         "hourly_cost": imp * inp.price[sl], "hourly_carbon_kg": imp * inp.carbon[sl]})


def slice_period(x: pd.DataFrame, period) -> pd.DataFrame:
    a, b = period
    return x.loc[(x["timestamp"] >= a) & (x["timestamp"] < b)]


def pareto_mask(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, float)
    keep = np.ones(len(values), dtype=bool)
    for i in range(len(values)):
        keep[i] = not np.any(np.all(values <= values[i], axis=1) & np.any(values < values[i], axis=1))
    return keep


def hypervolume_3d(points: np.ndarray, ref: np.ndarray) -> float:
    """Exact hypervolume (minimisation) by slicing along the third objective."""
    p = np.asarray(points, float)
    p = p[np.all(p < ref, axis=1)]
    if len(p) == 0:
        return 0.0
    p = p[pareto_mask(p)]
    p = p[np.argsort(p[:, 2])]
    total = 0.0
    for i in range(len(p)):
        z_hi = p[i + 1, 2] if i + 1 < len(p) else ref[2]
        if z_hi <= p[i, 2]:
            continue
        q = p[: i + 1, :2]
        q = q[pareto_mask(q)]
        q = q[np.argsort(q[:, 0])]
        area, prev_y = 0.0, ref[1]
        for x, y in q:
            if y < prev_y:
                area += (ref[0] - x) * (prev_y - y)
                prev_y = y
        total += area * (z_hi - p[i, 2])
    return total
