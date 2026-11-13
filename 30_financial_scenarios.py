#!/usr/bin/env python3
"""Illustrative battery investment thresholds, separate from operating KPIs.

The source price series does not identify a currency or a battery purchase cost.
All capital, maintenance, and wear inputs below are explicit *hypotheses in the
same unspecified source currency*. Repeating one observed building-year for ten
years is an accounting scenario, not a lifetime forecast or a market quote.
"""
from __future__ import annotations

import pandas as pd

from battery_study import config, data, metrics

OUT = config.RESULTS / "sensitivity"
YEARS = 10
DISCOUNT_RATE = 0.05
ANNUAL_OM_FRACTION_OF_CAPEX = 0.01
EXPORT_CREDITS = (0.0, 0.10)  # source currency units / exported kWh
WEAR_COSTS = (0.0, 0.05, 0.10)  # source currency units / AC throughput kWh
INSTALLED_COSTS_PER_KWH = (250.0, 500.0, 750.0)  # purely illustrative

RUNS = {
    "S1 PV priority": "rule_strategies/S1_hourly.csv",
    "S2 peak shaving": "rule_strategies/S2_hourly.csv",
    "S3 price response": "rule_strategies/S3_hourly.csv",
    "S4 carbon response": "rule_strategies/S4_hourly.csv",
    "S5 min peak": "s5_multiobjective/S5_min_peak_hourly.csv",
    "S5 balanced": "s5_multiobjective/S5_balanced_hourly.csv",
}


def annuity_factor(years: int, rate: float) -> float:
    if years <= 0 or rate < 0:
        raise ValueError("years must be positive and discount rate nonnegative")
    return float(sum((1.0 + rate) ** (-year) for year in range(1, years + 1)))


def annual_bill(import_cost: float, export_kwh: float, export_credit: float) -> float:
    return import_cost - export_credit * export_kwh


def npv(annual_saving: float, throughput_kwh: float, capex: float,
        wear_per_kwh: float, om_fraction: float = ANNUAL_OM_FRACTION_OF_CAPEX,
        years: int = YEARS, discount_rate: float = DISCOUNT_RATE) -> float:
    """Constant annual cash flow scenario; no resale, replacement or tax benefit."""
    if min(throughput_kwh, capex, wear_per_kwh, om_fraction) < 0:
        raise ValueError("scenario cost and throughput inputs must be nonnegative")
    net_annual = annual_saving - wear_per_kwh * throughput_kwh - om_fraction * capex
    return -capex + annuity_factor(years, discount_rate) * net_annual


def break_even_capex(annual_saving: float, throughput_kwh: float,
                     wear_per_kwh: float, om_fraction: float = ANNUAL_OM_FRACTION_OF_CAPEX,
                     years: int = YEARS, discount_rate: float = DISCOUNT_RATE) -> float:
    """Maximum up-front price yielding nonnegative NPV; negative means none."""
    a = annuity_factor(years, discount_rate)
    return a * (annual_saving - wear_per_kwh * throughput_kwh) / (1.0 + a * om_fraction)


def discounted_payback_year(annual_saving: float, throughput_kwh: float,
                            capex: float, wear_per_kwh: float,
                            om_fraction: float = ANNUAL_OM_FRACTION_OF_CAPEX,
                            years: int = YEARS, discount_rate: float = DISCOUNT_RATE):
    net_annual = annual_saving - wear_per_kwh * throughput_kwh - om_fraction * capex
    if net_annual <= 0:
        return None
    value = -capex
    for year in range(1, years + 1):
        value += net_annual / ((1.0 + discount_rate) ** year)
        if value >= -1e-9:
            return year
    return None


def main() -> None:
    inp = data.load_inputs()
    capacity = float(inp.battery["capacity"])
    base = metrics.kpis(metrics.no_battery_frame(inp), capacity_kwh=capacity)
    rows = []
    for strategy, rel_path in RUNS.items():
        frame = pd.read_csv(config.RESULTS / rel_path)
        k = metrics.kpis(frame, capacity_kwh=capacity)
        for credit in EXPORT_CREDITS:
            base_bill = annual_bill(base["electricity_cost_currency"], base["grid_export_kwh"], credit)
            policy_bill = annual_bill(k["electricity_cost_currency"], k["grid_export_kwh"], credit)
            saving = base_bill - policy_bill
            for wear in WEAR_COSTS:
                threshold = break_even_capex(saving, k["battery_ac_throughput_kwh"], wear)
                for capex_per_kwh in INSTALLED_COSTS_PER_KWH:
                    capex = capacity * capex_per_kwh
                    rows.append({
                        "strategy": strategy,
                        "export_credit_per_kwh": credit,
                        "wear_cost_per_ac_throughput_kwh": wear,
                        "installed_cost_per_kwh_capacity_assumed": capex_per_kwh,
                        "battery_capacity_kwh": capacity,
                        "capex_assumed": capex,
                        "s0_annual_bill": base_bill,
                        "policy_annual_bill": policy_bill,
                        "annual_bill_saving_vs_s0": saving,
                        "annual_ac_throughput_kwh": k["battery_ac_throughput_kwh"],
                        "annual_wear_cost_assumed": wear * k["battery_ac_throughput_kwh"],
                        "annual_om_cost_assumed": ANNUAL_OM_FRACTION_OF_CAPEX * capex,
                        "break_even_capex": threshold,
                        "break_even_installed_cost_per_kwh_capacity": threshold / capacity,
                        "npv_10y_5pct": npv(saving, k["battery_ac_throughput_kwh"], capex, wear),
                        "discounted_payback_year_within_10y": discounted_payback_year(
                            saving, k["battery_ac_throughput_kwh"], capex, wear),
                    })
    OUT.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "financial_scenario_grid.csv", index=False)
    concise = table.loc[(table.export_credit_per_kwh == 0) &
                        (table.wear_cost_per_ac_throughput_kwh == 0.05) &
                        (table.installed_cost_per_kwh_capacity_assumed == 500)].copy()
    concise.to_csv(OUT / "financial_scenario_example.csv", index=False)
    print(concise[["strategy", "annual_bill_saving_vs_s0", "annual_wear_cost_assumed",
                   "break_even_capex", "npv_10y_5pct",
                   "discounted_payback_year_within_10y"]].round(2).to_string(index=False))
    print("\nAll capital and wear inputs are hypothetical; no actual purchase quote or currency is supplied.")


if __name__ == "__main__":
    main()
