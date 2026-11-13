#!/usr/bin/env python3
"""Sensitivity analyses.

(a) Boundary SOC: calibration and hold-out windows are each simulated on their
    own with initial SOC = 0, 50 % or 100 % of capacity (free terminal SOC) and
    with a periodic boundary. Rankings of S1-S5 on each objective are compared.
(b) Export credit: full-year net cost when exports earn a flat feed-in tariff of
    0, 0.05, 0.10 or 0.21 currency/kWh (0.21 = lowest import tariff).
"""
from __future__ import annotations
import glob
import numpy as np
import pandas as pd
from battery_study import config, data, battery, metrics, registry

OUT = config.RESULTS / "sensitivity"
KEYS = list(metrics.KEYS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inp = data.load_inputs(); cap = float(inp.battery["capacity"])
    pols = registry.rule_policies(inp)
    rows = []
    for window, (a, b) in (("calibration", config.CALIBRATION), ("holdout", config.HOLDOUT)):
        for name, pol in pols.items():
            for label, soc0 in (("SOC0=0%", 0.0), ("SOC0=50%", 0.5 * cap), ("SOC0=100%", cap), ("periodic", None)):
                x = (battery.simulate_periodic(inp, pol, a, b) if soc0 is None
                     else battery.simulate(inp, pol, a, b, initial_soc=soc0))
                k = metrics.kpis(x)
                rows.append({"window": window, "boundary": label, "strategy": name,
                             **{kk: k[kk] for kk in KEYS + ["mean_monthly_peak_kw", "soc_start_kwh", "soc_end_kwh"]}})
    t = pd.DataFrame(rows)
    s1 = t.loc[t.strategy.eq("S1 PV priority")].set_index(["window", "boundary"])[KEYS]
    for k in KEYS:
        t[f"{k}_change_vs_S1_pct"] = [100 * (r[k] / s1.loc[(r.window, r.boundary), k] - 1) for _, r in t.iterrows()]
        t[f"{k}_rank"] = t.groupby(["window", "boundary"])[k].rank(method="min")
    t.to_csv(OUT / "boundary_soc_sensitivity.csv", index=False)
    # Rank stability: for each window/objective, does the rank order change with the boundary?
    stab = []
    for (w, s), g in t.groupby(["window", "strategy"]):
        stab.append({"window": w, "strategy": s, **{f"{k}_rank_range": f"{int(g[k+'_rank'].min())}-{int(g[k+'_rank'].max())}" for k in KEYS},
                     **{f"{k}_change_vs_S1_pct_range": f"{g[k+'_change_vs_S1_pct'].min():.1f} to {g[k+'_change_vs_S1_pct'].max():.1f}" for k in KEYS}})
    pd.DataFrame(stab).to_csv(OUT / "boundary_soc_rank_stability.csv", index=False)

    # (b) feed-in credit on the reported full-year (periodic) runs
    files = {"S0 no battery": None}
    for f in sorted(glob.glob(str(config.RESULTS / "*" / "*_hourly.csv"))):
        files[f] = f
    fit_rows = []
    for key, f in files.items():
        if f is None:
            x = metrics.no_battery_frame(inp); name = key
        else:
            x = pd.read_csv(f); name = f.split("/")[-1].replace("_hourly.csv", "")
        for fit in (0.0, 0.05, 0.10, 0.21):
            fit_rows.append({"run": name, "feed_in_tariff": fit,
                             "net_cost_currency": float(x.hourly_cost.sum() - fit * x.grid_export_kwh.sum()),
                             "grid_export_kwh": float(x.grid_export_kwh.sum())})
    fit = pd.DataFrame(fit_rows)
    fit["rank_within_tariff"] = fit.groupby("feed_in_tariff").net_cost_currency.rank(method="min")
    fit.to_csv(OUT / "feed_in_tariff_sensitivity.csv", index=False)
    print(pd.DataFrame(stab).to_string(index=False))
    print(fit.pivot(index="run", columns="feed_in_tariff", values="net_cost_currency").round(1).to_string())


if __name__ == "__main__":
    main()
