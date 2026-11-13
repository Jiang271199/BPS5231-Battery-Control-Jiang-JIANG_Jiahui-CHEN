#!/usr/bin/env python3
"""S0-S4: no battery, PV priority, peak shaving, price response, carbon response.

All parameter searches score candidates on the calibration window only
(steps 1-5832, periodic SOC boundary). Selected parameters are frozen and the
full year is then simulated with a periodic boundary; calibration, hold-out
and full-year KPIs are slices of that single run.
"""
from __future__ import annotations
import itertools
import numpy as np
import pandas as pd
from battery_study import config, data, controllers as C, metrics, evaluate as E

OUT = config.RESULTS / "rule_strategies"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inp = data.load_inputs()
    cal_imp = data.calibration_import(inp)
    a, b = config.CALIBRATION
    kpi_tables, selected, all_checks = [], {}, []

    # S0 no battery (reference, no simulation needed)
    s0 = metrics.no_battery_frame(inp)
    kpi_tables.append(pd.DataFrame([{"strategy": "S0 no battery", "period": p,
                                     **metrics.kpis(metrics.slice_period(s0, r))}
                                    for p, r in config.PERIODS.items()]))

    # S1 PV priority
    s1_cal = E.score_calibration(inp, C.s1_pv_priority(inp))
    x, k, ch = E.report(inp, C.s1_pv_priority(inp), "S1 PV priority")
    x.to_csv(OUT / "S1_hourly.csv", index=False); kpi_tables.append(k); all_checks.append(ch.assign(strategy="S1"))

    # S2 peak shaving: same 4 x 3 grid as the interim study.
    cal = inp.df.iloc[a:b]
    top = cal.loc[cal_imp.to_numpy() >= cal_imp.quantile(0.99), "hour"]
    event_hours = sorted(top.value_counts().head(3).index.astype(int).tolist())
    charge_hours = sorted({((h - d - 1) % 24) + 1 for h in event_hours for d in (1, 2, 3)})
    ceiling = float(cal_imp.quantile(0.60))
    rows = []
    for q, r in itertools.product((0.90, 0.95, 0.975, 0.995), (0.25, 0.50, 0.75)):
        tgt = float(cal_imp.quantile(q))
        m = E.score_calibration(inp, C.s2_peak_shaving(inp, tgt, r, ceiling, charge_hours))
        ok = (m["electricity_cost_currency"] <= 1.05 * s1_cal["electricity_cost_currency"]
              and m["carbon_emissions_kgco2"] <= 1.05 * s1_cal["carbon_emissions_kgco2"])
        rows.append({"target_quantile": q, "target_kw": tgt, "reserve_fraction": r,
                     "charging_ceiling_kw": ceiling, "calibration_feasible": ok, **m})
    search = pd.DataFrame(rows); search.to_csv(OUT / "S2_calibration_search.csv", index=False)
    ch2 = search.loc[search.calibration_feasible].sort_values(
        ["peak_grid_import_kw", "electricity_cost_currency", "battery_ac_throughput_kwh"]).iloc[0]
    p2 = dict(target_kw=float(ch2.target_kw), reserve_fraction=float(ch2.reserve_fraction),
              ceiling_kw=ceiling, charge_hours=charge_hours)
    selected["S2 peak shaving"] = {**p2, "target_quantile": float(ch2.target_quantile),
                                   "event_hours": event_hours,
                                   "rule": "min calibration peak s.t. cost and carbon <= 1.05 x S1"}
    x, k, ch = E.report(inp, C.s2_peak_shaving(inp, **p2), "S2 peak shaving")
    x.to_csv(OUT / "S2_hourly.csv", index=False); kpi_tables.append(k); all_checks.append(ch.assign(strategy="S2"))

    # Charging-ceiling candidates for S3/S4. The interim study fixed the ceiling at
    # the calibration no-battery maximum, which let grid charging create a new
    # 4.94 kW peak in the hold-out. The ceiling is now searched.
    ceilings = {"P60": float(cal_imp.quantile(0.60)), "P90": float(cal_imp.quantile(0.90)),
                "no-battery max": float(cal_imp.max())}

    # S3 price response
    levels = sorted(np.unique(inp.price[a:b]).tolist())
    rows = []
    for lo, hi in itertools.product(levels[:-1], levels[1:]):
        if lo >= hi:
            continue
        for ms, (cn, cv) in itertools.product((0.50, 0.75, 1.00), ceilings.items()):
            m = E.score_calibration(inp, C.s3_price_response(inp, lo, hi, ms, cv))
            rows.append({"low_price": lo, "high_price": hi, "max_soc_fraction": ms,
                         "ceiling_label": cn, "charge_ceiling_kw": cv, **m})
    search = pd.DataFrame(rows); search.to_csv(OUT / "S3_calibration_search.csv", index=False)
    c3 = search.sort_values(["electricity_cost_currency", "peak_grid_import_kw", "battery_ac_throughput_kwh"]).iloc[0]
    p3 = dict(low=float(c3.low_price), high=float(c3.high_price), max_soc=float(c3.max_soc_fraction),
              ceiling_kw=float(c3.charge_ceiling_kw))
    selected["S3 price response"] = {**p3, "ceiling_label": c3.ceiling_label, "rule": "min calibration cost"}
    def s3_checks(x):
        g = x.battery_charge_input_kwh.gt(2e-5) & x.baseline_net_kwh.ge(0)
        d = x.battery_discharge_output_kwh.gt(2e-5) & x.baseline_net_kwh.gt(0)
        return {"grid charging only at low tariff": (x.loc[g, "price_per_kwh"] <= p3["low"] + 1e-8).all(),
                "charging-hour import ceiling": (x.loc[g, "grid_import_kwh"] <= p3["ceiling_kw"] + 1e-8).all(),
                "discharge only at high tariff": (x.loc[d, "price_per_kwh"] >= p3["high"] - 1e-8).all()}
    x, k, ch = E.report(inp, C.s3_price_response(inp, **p3), "S3 price response", s3_checks)
    x.to_csv(OUT / "S3_hourly.csv", index=False); kpi_tables.append(k); all_checks.append(ch.assign(strategy="S3"))

    # S4 carbon response
    rows = []
    for lq, hq in itertools.product((0.1, 0.2, 0.3, 0.4), (0.6, 0.7, 0.8, 0.9)):
        lo = float(np.quantile(inp.carbon[a:b], lq)); hi = float(np.quantile(inp.carbon[a:b], hq))
        for ms, (cn, cv) in itertools.product((0.50, 0.75, 1.00), ceilings.items()):
            m = E.score_calibration(inp, C.s4_carbon_response(inp, lo, hi, ms, cv))
            rows.append({"low_quantile": lq, "high_quantile": hq, "low_carbon": lo, "high_carbon": hi,
                         "max_soc_fraction": ms, "ceiling_label": cn, "charge_ceiling_kw": cv, **m})
    search = pd.DataFrame(rows); search.to_csv(OUT / "S4_calibration_search.csv", index=False)
    c4 = search.sort_values(["carbon_emissions_kgco2", "electricity_cost_currency", "peak_grid_import_kw"]).iloc[0]
    p4 = dict(low=float(c4.low_carbon), high=float(c4.high_carbon), max_soc=float(c4.max_soc_fraction),
              ceiling_kw=float(c4.charge_ceiling_kw))
    selected["S4 carbon response"] = {**p4, "low_quantile": float(c4.low_quantile),
                                      "high_quantile": float(c4.high_quantile),
                                      "ceiling_label": c4.ceiling_label, "rule": "min calibration carbon"}
    def s4_checks(x):
        g = x.battery_charge_input_kwh.gt(2e-5) & x.baseline_net_kwh.ge(0)
        d = x.battery_discharge_output_kwh.gt(2e-5) & x.baseline_net_kwh.gt(0)
        return {"grid charging only at low carbon": (x.loc[g, "carbon_intensity_kg_per_kwh"] <= p4["low"] + 1e-8).all(),
                "charging-hour import ceiling": (x.loc[g, "grid_import_kwh"] <= p4["ceiling_kw"] + 1e-8).all(),
                "discharge only at high carbon": (x.loc[d, "carbon_intensity_kg_per_kwh"] >= p4["high"] - 1e-8).all()}
    x, k, ch = E.report(inp, C.s4_carbon_response(inp, **p4), "S4 carbon response", s4_checks)
    x.to_csv(OUT / "S4_hourly.csv", index=False); kpi_tables.append(k); all_checks.append(ch.assign(strategy="S4"))

    kpi = pd.concat(kpi_tables, ignore_index=True); kpi.to_csv(OUT / "S0_S4_kpis.csv", index=False)
    pd.concat(all_checks, ignore_index=True).to_csv(OUT / "validation_checks.csv", index=False)
    E.write_json(OUT / "selected_parameters.json", selected)
    print(kpi.loc[kpi.period.eq("full_year"), ["strategy", "electricity_cost_currency", "carbon_emissions_kgco2",
                                              "peak_grid_import_kw", "grid_export_kwh"]].round(3).to_string(index=False))
    print(kpi.loc[kpi.period.eq("holdout"), ["strategy", "electricity_cost_currency", "carbon_emissions_kgco2",
                                            "peak_grid_import_kw"]].round(3).to_string(index=False))
    print(selected)


if __name__ == "__main__":
    main()
