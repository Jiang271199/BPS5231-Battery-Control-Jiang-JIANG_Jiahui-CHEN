#!/usr/bin/env python3
"""S6 MPC benchmarks (perfect and day-ahead persistence forecasts) and annual LP bounds."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from battery_study import config, data, metrics, evaluate as E, battery, validation
from battery_study.mpc import RollingMPC, annual_bound

OUT = config.RESULTS / "s6_mpc"


def carbon_weight(inp):
    # Equal-value weighting: one kgCO2 is worth the average calibration import
    # price divided by the average calibration carbon intensity (currency/kgCO2).
    a, b = config.CALIBRATION
    return float(inp.price[a:b].mean() / inp.carbon[a:b].mean())


def configs(lc):
    return {
        "S6 MPC perfect cost-only": ("perfect", 1.0, 0.0, 0.0),
        "S6 MPC perfect cost+peak": ("perfect", 1.0, 0.0, 0.5),
        "S6 MPC perfect balanced": ("perfect", 1.0, lc, 0.5),
        "S6 MPC perfect peak-heavy": ("perfect", 1.0, lc, 2.0),
        "S6 MPC persistence cost+peak": ("persistence", 1.0, 0.0, 0.5),
        "S6 MPC persistence balanced": ("persistence", 1.0, lc, 0.5),
    }


def run_one(item):
    name, (fc, wp, wc, wk) = item
    inp = data.load_inputs()
    pol = RollingMPC(inp, fc, wp, wc, wk)
    x = battery.simulate_periodic(inp, pol, max_passes=6)
    return name, x, pol.failures


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inp = data.load_inputs(); lc = carbon_weight(inp)
    cfg = configs(lc)
    kpis, checks, meta = [], [], []
    with ProcessPoolExecutor(max_workers=2) as ex:
        for name, x, fails in ex.map(run_one, cfg.items()):
            ch = validation.validate(x, periodic=True)
            if not ch.passed.all():
                raise AssertionError(name + "\n" + ch.loc[~ch.passed].to_string())
            slug = name.replace("S6 MPC ", "").replace(" ", "_").replace("+", "_")
            x.to_csv(OUT / f"S6_{slug}_hourly.csv", index=False)
            for p, r in config.PERIODS.items():
                kpis.append({"strategy": name, "period": p, **metrics.kpis(metrics.slice_period(x, r))})
            checks.append(ch.assign(strategy=name))
            fc, wp, wc, wk = cfg[name]
            meta.append({"strategy": name, "forecast": fc, "w_price": wp, "w_carbon_currency_per_kg": wc,
                         "w_peak_currency_per_kw": wk, "lp_failures": fails,
                         "periodic_passes": x.attrs["periodic_passes"]})
            print("done", name, flush=True)
    kpi = pd.DataFrame(kpis); kpi.to_csv(OUT / "S6_kpis.csv", index=False)
    pd.DataFrame(meta).to_csv(OUT / "S6_configurations.csv", index=False)
    pd.concat(checks).to_csv(OUT / "validation_checks.csv", index=False)

    bounds = []
    for obj in ("cost", "carbon", "peak"):
        bounds.append({"bound": f"LP bound: min {obj}", "objective": obj, "peak_cap_kw": np.nan, **annual_bound(inp, obj)})
    for cap in (4.5, 4.0, 3.5, 3.0, 2.5):
        bounds.append({"bound": f"LP bound: min cost, peak<={cap}", "objective": "cost", "peak_cap_kw": cap,
                       **annual_bound(inp, "cost", peak_cap=cap)})
    bounds = pd.DataFrame(bounds); bounds.to_csv(OUT / "LP_annual_bounds.csv", index=False)
    E.write_json(OUT / "S6_notes.json", {"horizon_h": 24, "carbon_weight_currency_per_kg": lc,
                 "linear_battery_one_way_efficiency": 0.9 ** 0.5,
                 "persistence_forecast": "net load and carbon from the same hour of the previous day; tariff known"})
    k = kpi.loc[kpi.period.eq("full_year"), ["strategy", *metrics.KEYS, "grid_export_kwh"]]
    print(k.round(3).to_string(index=False)); print(bounds.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
