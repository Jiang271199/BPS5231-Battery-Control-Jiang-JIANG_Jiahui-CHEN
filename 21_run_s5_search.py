#!/usr/bin/env python3
"""S5 multi-objective rule: ParEGO search on the calibration window (seed 5231),
Pareto selection among S5 candidates, then frozen full-year periodic evaluation."""
from __future__ import annotations
import numpy as np
import pandas as pd
from battery_study import config, data, controllers as C, metrics, evaluate as E, search

OUT = config.RESULTS / "s5_multiobjective"
KEYS = list(metrics.KEYS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inp = data.load_inputs()
    cal_imp = data.calibration_import(inp)
    bounds = C.s5_bounds(inp, cal_imp)
    hist = pd.DataFrame(search.run(inp, cal_imp, bounds, "parego", config.S5_SEED))
    hist.to_csv(OUT / "S5_search_history.csv", index=False)
    assert (hist.periodic_residual_kwh <= config.PERIODIC_TOL_KWH).all()
    front = hist.loc[metrics.pareto_mask(hist[KEYS].to_numpy())].copy()
    front.to_csv(OUT / "S5_pareto_calibration.csv", index=False)
    picks = {"min_cost": front.electricity_cost_currency.idxmin(),
             "min_carbon": front.carbon_emissions_kgco2.idxmin(),
             "min_peak": front.peak_grid_import_kw.idxmin()}
    v = front[KEYS].to_numpy(); nv = (v - v.min(0)) / (np.ptp(v, 0) + 1e-9)
    picks["balanced"] = front.index[int(np.linalg.norm(nv, axis=1).argmin())]
    kpis, params, checks = [], [], []
    PKEYS = ("w_price", "w_carbon", "w_peak", "target_kw", "reserve_fraction", "max_grid_charge_soc",
             "charge_score", "discharge_score", "charge_ceiling_kw")
    for name, idx in picks.items():
        row = hist.loc[idx]
        p = {k: float(row[k]) for k in PKEYS}
        x, k, ch = E.report(inp, C.s5_score_policy(inp, p, bounds), f"S5 {name}")
        x.to_csv(OUT / f"S5_{name}_hourly.csv", index=False)
        kpis.append(k); checks.append(ch.assign(strategy=f"S5 {name}"))
        params.append({"solution": name, "evaluation": int(row.evaluation), **p,
                       "target_quantile": float(row.target_quantile)})
    kpi = pd.concat(kpis, ignore_index=True); kpi.to_csv(OUT / "S5_selected_kpis.csv", index=False)
    pd.DataFrame(params).to_csv(OUT / "S5_selected_parameters.csv", index=False)
    pd.concat(checks, ignore_index=True).to_csv(OUT / "validation_checks.csv", index=False)
    E.write_json(OUT / "S5_summary.json", {
        "algorithm": "ParEGO: augmented-Chebyshev random scalarisation, GP (Matern 5/2 ARD + white noise, "
                     "hyperparameters fitted by marginal likelihood), expected improvement over 2000 uniform "
                     "+ 400 local proposals", "seed": config.S5_SEED,
        "initial_evaluations": search.N_INITIAL, "total_evaluations": search.N_TOTAL,
        "normalisation_bounds_from_calibration": bounds, "pareto_candidates": int(len(front)),
        "selected_evaluations": {k: int(hist.loc[i, "evaluation"]) for k, i in picks.items()},
        "boundary": "periodic SOC on the calibration window during search; periodic full year for reporting"})
    print(len(front), "Pareto candidates")
    print(kpi[["strategy", "period", *KEYS, "grid_export_kwh"]].round(3).to_string(index=False))
    print(pd.DataFrame(params).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
