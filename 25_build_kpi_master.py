#!/usr/bin/env python3
"""Unified S0-S6 KPI master table (+ annual LP bounds) with changes relative to S1."""
from __future__ import annotations
import numpy as np
import pandas as pd
from battery_study import config, metrics

OUT = config.RESULTS
REL = ["electricity_cost_currency", "carbon_emissions_kgco2", "peak_grid_import_kw",
       "mean_monthly_peak_kw", "grid_export_kwh"]


def main():
    k = pd.concat([pd.read_csv(OUT / "rule_strategies" / "S0_S4_kpis.csv"),
                   pd.read_csv(OUT / "s5_multiobjective" / "S5_selected_kpis.csv"),
                   pd.read_csv(OUT / "s6_mpc" / "S6_kpis.csv")], ignore_index=True)
    # min_cost and min_carbon can be the same S5 candidate; keep one row, relabelled.
    sel = pd.read_csv(OUT / "s5_multiobjective" / "S5_selected_parameters.csv").set_index("solution")
    if sel.loc["min_cost", "evaluation"] == sel.loc["min_carbon", "evaluation"]:
        k = k.loc[~k.strategy.eq("S5 min_carbon")]
        k.loc[k.strategy.eq("S5 min_cost"), "strategy"] = "S5 min_cost = min_carbon"
    s1 = k.loc[k.strategy.eq("S1 PV priority")].set_index("period")
    for c in REL:
        k[c + "_change_vs_S1_pct"] = [100 * (r[c] / s1.loc[r.period, c] - 1) for _, r in k.iterrows()]
    lp = pd.read_csv(OUT / "s6_mpc" / "LP_annual_bounds.csv").rename(columns={"bound": "strategy"})
    lp["period"] = "full_year"
    for c in ("electricity_cost_currency", "carbon_emissions_kgco2", "peak_grid_import_kw", "grid_export_kwh"):
        lp[c + "_change_vs_S1_pct"] = 100 * (lp[c] / s1.loc["full_year", c] - 1)
    master = pd.concat([k, lp.drop(columns=["objective", "peak_cap_kw"])], ignore_index=True)
    # A within-S5 Pareto candidate may be dominated by another reported rule.
    # Keep this comparison separate from oracle MPC and relaxed LP benchmarks.
    master["pareto_among_reported_rules"] = pd.NA
    master["dominated_by_reported_rule"] = ""
    pareto_rows = []
    for period in ("calibration", "holdout", "full_year"):
        section = master.loc[master.period.eq(period) & master.strategy.str.match(r"^S[0-5] ")]
        values = section[list(metrics.KEYS)].to_numpy(dtype=float)
        names = section.strategy.to_list()
        for pos, (idx, row) in enumerate(section.iterrows()):
            dominates = np.all(values <= values[pos], axis=1) & np.any(values < values[pos], axis=1)
            dominators = [names[j] for j in np.flatnonzero(dominates)]
            master.at[idx, "pareto_among_reported_rules"] = not bool(dominators)
            master.at[idx, "dominated_by_reported_rule"] = "; ".join(dominators)
            pareto_rows.append({"period": period, "strategy": row.strategy,
                                **{key: row[key] for key in metrics.KEYS},
                                "pareto_among_reported_rules": not bool(dominators),
                                "dominated_by_reported_rule": "; ".join(dominators)})
    pd.DataFrame(pareto_rows).to_csv(OUT / "Pareto_reported_rules.csv", index=False)
    master.to_csv(OUT / "KPI_master_table.csv", index=False)

    cols = ["strategy", "electricity_cost_currency", "carbon_emissions_kgco2", "peak_grid_import_kw",
            "mean_monthly_peak_kw", "grid_export_kwh", "equivalent_full_cycles"]
    lines = ["# KPI master table", "",
             "Periodic SOC boundary. Cost and carbon count imports only. Peak = maximum hourly-average import (kW). "
             "Percentages are changes relative to S1 in the same period. LP rows are relaxation bounds, not controllers. "
             "The Pareto flag compares only the reported S0–S5 rule solutions in that period; it does not include "
             "oracle MPC or the LP relaxation.", ""]
    for period in ("full_year", "calibration", "holdout"):
        t = master.loc[master.period.eq(period)].copy()
        lines += [f"## {period.replace('_', ' ').title()}", "",
                  "| Strategy | Cost | Δ cost | Carbon (kgCO2) | Δ carbon | Peak (kW) | Δ peak | Mean monthly peak (kW) | Export (kWh) | EFC | Rule Pareto |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"]
        for _, r in t.iterrows():
            f = lambda v, d=1: "" if pd.isna(v) else f"{v:,.{d}f}"
            p = lambda v: "" if pd.isna(v) else f"{v:+.1f}%"
            lines.append(f"| {r.strategy} | {f(r.electricity_cost_currency)} | {p(r.electricity_cost_currency_change_vs_S1_pct)} | "
                         f"{f(r.carbon_emissions_kgco2)} | {p(r.carbon_emissions_kgco2_change_vs_S1_pct)} | "
                         f"{f(r.peak_grid_import_kw, 3)} | {p(r.peak_grid_import_kw_change_vs_S1_pct)} | "
                         f"{f(r.get('mean_monthly_peak_kw'), 3)} | {f(r.grid_export_kwh, 0)} | "
                         f"{f(r.get('equivalent_full_cycles'), 0)} | "
                         f"{'Yes' if r.pareto_among_reported_rules is True else 'No' if r.pareto_among_reported_rules is False else ''} |")
        lines.append("")
    (OUT / "KPI_master_table.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
