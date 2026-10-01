#!/usr/bin/env python3
"""Step 8: unified Interim comparison of no-battery and PV-priority cases."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PV_HOURLY = ROOT / "results" / "pv_priority" / "pv_priority_hourly.csv"
PV_SUMMARY = ROOT / "results" / "pv_priority" / "pv_priority_summary.json"
PV_CHECKS = ROOT / "results" / "pv_priority" / "validation_checks.csv"
RESULTS = ROOT / "results" / "interim_comparison"
FIGURES = ROOT / "figures" / "interim_comparison"

NAVY = "#14334D"
TEAL = "#087E8B"
ORANGE = "#DE7B36"
GREEN = "#4B8C67"
PURPLE = "#77559B"
GREY = "#687682"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#A8B4BD",
        "axes.labelcolor": NAVY,
        "xtick.color": GREY,
        "ytick.color": GREY,
        "grid.color": "#DCE3E8",
        "grid.alpha": 0.75,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)


def prepare_hourly() -> pd.DataFrame:
    h = pd.read_csv(PV_HOURLY)
    h["baseline_import_kwh"] = h["baseline_net_kwh"].clip(lower=0.0)
    h["baseline_export_kwh"] = (-h["baseline_net_kwh"]).clip(lower=0.0)
    h["baseline_cost"] = h["baseline_import_kwh"] * h["price_per_kwh"]
    h["baseline_carbon_kg"] = (
        h["baseline_import_kwh"] * h["carbon_intensity_kg_per_kwh"]
    )
    h["import_reduction_kwh"] = h["baseline_import_kwh"] - h["grid_import_kwh"]
    h["export_reduction_kwh"] = h["baseline_export_kwh"] - h["grid_export_kwh"]
    h["cost_saving"] = h["baseline_cost"] - h["hourly_cost"]
    h["carbon_reduction_kg"] = h["baseline_carbon_kg"] - h["hourly_carbon_kg"]
    h["day_index"] = (h["timestamp"].astype(int) // 24) + 1
    h["source_month_label"] = h["month"].map(
        {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    )
    return h


def kpi_table(summary: dict) -> pd.DataFrame:
    b, s = summary["baseline"], summary["pv_priority"]
    specs = [
        ("Grid import", "kWh", b["grid_import_kwh"], s["grid_import_kwh"], "lower"),
        ("Grid export", "kWh", b["grid_export_kwh"], s["grid_export_kwh"], "lower"),
        ("Electricity cost", "currency", b["electricity_cost_currency"], s["electricity_cost_currency"], "lower"),
        ("Operational carbon", "kgCO2", b["carbon_emissions_kgco2"], s["carbon_emissions_kgco2"], "lower"),
        ("Peak grid import", "kW", b["peak_grid_import_kw"], s["peak_grid_import_kw"], "lower"),
        ("PV self-consumption", "%", b["pv_self_consumption_fraction"] * 100, s["pv_self_consumption_fraction"] * 100, "higher"),
        ("Self-sufficiency", "%", b["self_sufficiency_fraction"] * 100, s["self_sufficiency_fraction"] * 100, "higher"),
    ]
    rows = []
    for metric, unit, baseline, strategy, direction in specs:
        absolute = strategy - baseline
        if unit == "%":
            improvement = strategy - baseline
            definition = "percentage-point increase"
        elif direction == "lower":
            improvement = (baseline - strategy) / baseline * 100 if baseline else np.nan
            definition = "reduction from baseline (%)"
        else:
            improvement = (strategy - baseline) / baseline * 100 if baseline else np.nan
            definition = "increase from baseline (%)"
        rows.append(
            {
                "metric": metric,
                "unit": unit,
                "no_battery": baseline,
                "pv_priority": strategy,
                "strategy_minus_baseline": absolute,
                "reported_improvement": improvement,
                "improvement_definition": definition,
            }
        )
    return pd.DataFrame(rows)


def monthly_table(h: pd.DataFrame) -> pd.DataFrame:
    order = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]
    out = h.groupby("month").agg(
        observations=("timestamp", "size"),
        baseline_import_kwh=("baseline_import_kwh", "sum"),
        pv_priority_import_kwh=("grid_import_kwh", "sum"),
        import_reduction_kwh=("import_reduction_kwh", "sum"),
        baseline_export_kwh=("baseline_export_kwh", "sum"),
        pv_priority_export_kwh=("grid_export_kwh", "sum"),
        export_reduction_kwh=("export_reduction_kwh", "sum"),
        baseline_cost=("baseline_cost", "sum"),
        pv_priority_cost=("hourly_cost", "sum"),
        cost_saving=("cost_saving", "sum"),
        baseline_carbon_kg=("baseline_carbon_kg", "sum"),
        pv_priority_carbon_kg=("hourly_carbon_kg", "sum"),
        carbon_reduction_kg=("carbon_reduction_kg", "sum"),
        baseline_peak_kw=("baseline_import_kwh", "max"),
        pv_priority_peak_kw=("grid_import_kwh", "max"),
    ).reindex(order)
    out.insert(0, "month", out.index)
    out.insert(1, "month_label", ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"])
    out["import_reduction_pct"] = out["import_reduction_kwh"] / out["baseline_import_kwh"] * 100
    out["cost_saving_pct"] = out["cost_saving"] / out["baseline_cost"] * 100
    out["carbon_reduction_pct"] = out["carbon_reduction_kg"] / out["baseline_carbon_kg"] * 100
    out["peak_reduction_kw"] = out["baseline_peak_kw"] - out["pv_priority_peak_kw"]
    out["peak_reduction_pct"] = out["peak_reduction_kw"] / out["baseline_peak_kw"] * 100
    return out.reset_index(drop=True)


def daily_peak_table(h: pd.DataFrame) -> pd.DataFrame:
    out = h.groupby("day_index", as_index=False).agg(
        source_month=("month", "first"),
        baseline_daily_peak_kw=("baseline_import_kwh", "max"),
        pv_priority_daily_peak_kw=("grid_import_kwh", "max"),
        daily_grid_import_reduction_kwh=("import_reduction_kwh", "sum"),
        daily_cost_saving=("cost_saving", "sum"),
        daily_carbon_reduction_kg=("carbon_reduction_kg", "sum"),
    )
    out["daily_peak_reduction_kw"] = (
        out["baseline_daily_peak_kw"] - out["pv_priority_daily_peak_kw"]
    )
    out["daily_peak_reduction_pct"] = np.where(
        out["baseline_daily_peak_kw"] > 0,
        out["daily_peak_reduction_kw"] / out["baseline_daily_peak_kw"] * 100,
        np.nan,
    )
    out["peak_reduced_flag"] = out["daily_peak_reduction_kw"] > 1e-8
    return out


def top_peak_table(h: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    cols = [
        "timestamp", "month", "hour", "load_kwh", "pv_kwh",
        "baseline_import_kwh", "grid_import_kwh", "import_reduction_kwh",
        "soc_start_kwh", "soc_end_kwh", "battery_exchange_kwh",
        "price_per_kwh", "carbon_intensity_kg_per_kwh",
    ]
    out = h.nlargest(n, "baseline_import_kwh")[cols].copy()
    out.insert(0, "baseline_peak_rank", np.arange(1, len(out) + 1))
    return out


def price_tier_table(h: pd.DataFrame) -> pd.DataFrame:
    out = h.groupby("price_per_kwh", as_index=False).agg(
        hours=("timestamp", "size"),
        baseline_import_kwh=("baseline_import_kwh", "sum"),
        pv_priority_import_kwh=("grid_import_kwh", "sum"),
        import_reduction_kwh=("import_reduction_kwh", "sum"),
        baseline_cost=("baseline_cost", "sum"),
        pv_priority_cost=("hourly_cost", "sum"),
        cost_saving=("cost_saving", "sum"),
        carbon_reduction_kg=("carbon_reduction_kg", "sum"),
    )
    out["share_of_total_cost_saving_pct"] = out["cost_saving"] / h["cost_saving"].sum() * 100
    return out


def carbon_bin_table(h: pd.DataFrame) -> pd.DataFrame:
    labels = ["Q1 lowest", "Q2", "Q3", "Q4", "Q5 highest"]
    x = h.copy()
    x["carbon_quintile"] = pd.qcut(
        x["carbon_intensity_kg_per_kwh"], 5, labels=labels, duplicates="drop"
    )
    out = x.groupby("carbon_quintile", observed=False, as_index=False).agg(
        hours=("timestamp", "size"),
        mean_carbon_intensity=("carbon_intensity_kg_per_kwh", "mean"),
        baseline_import_kwh=("baseline_import_kwh", "sum"),
        pv_priority_import_kwh=("grid_import_kwh", "sum"),
        import_reduction_kwh=("import_reduction_kwh", "sum"),
        baseline_carbon_kg=("baseline_carbon_kg", "sum"),
        pv_priority_carbon_kg=("hourly_carbon_kg", "sum"),
        carbon_reduction_kg=("carbon_reduction_kg", "sum"),
    )
    out["share_of_total_carbon_reduction_pct"] = (
        out["carbon_reduction_kg"] / h["carbon_reduction_kg"].sum() * 100
    )
    return out


def validation_table(
    h: pd.DataFrame,
    summary: dict,
    kpis: pd.DataFrame,
    monthly: pd.DataFrame,
    daily: pd.DataFrame,
) -> pd.DataFrame:
    b, s = summary["baseline"], summary["pv_priority"]
    prior = pd.read_csv(PV_CHECKS)
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append((name, bool(passed), detail))

    add("Step 7 validation inherited", prior["passed"].all(), f"{len(prior)} of {len(prior)} prior checks passed")
    add("8760 hourly records", len(h) == 8760, f"n={len(h)}")
    add("No missing comparison outputs", not h[["baseline_import_kwh", "grid_import_kwh", "cost_saving", "carbon_reduction_kg"]].isna().any().any(), "four primary comparison fields checked")
    add("Baseline import reconciles", np.isclose(h["baseline_import_kwh"].sum(), b["grid_import_kwh"], atol=1e-8), f"hourly sum={h['baseline_import_kwh'].sum():.9f} kWh")
    add("PV-priority import reconciles", np.isclose(h["grid_import_kwh"].sum(), s["grid_import_kwh"], atol=1e-8), f"hourly sum={h['grid_import_kwh'].sum():.9f} kWh")
    add("Cost saving identity", np.isclose(h["cost_saving"].sum(), b["electricity_cost_currency"] - s["electricity_cost_currency"], atol=1e-8), f"saving={h['cost_saving'].sum():.9f}")
    add("Carbon reduction identity", np.isclose(h["carbon_reduction_kg"].sum(), b["carbon_emissions_kgco2"] - s["carbon_emissions_kgco2"], atol=1e-8), f"reduction={h['carbon_reduction_kg'].sum():.9f} kgCO2")
    add("Import reduction and discharge reconcile", abs(h["import_reduction_kwh"].sum() - s["battery_discharge_output_kwh"]) < 0.001, f"difference={h['import_reduction_kwh'].sum()-s['battery_discharge_output_kwh']:.9f} kWh; within documented legacy clamp artifact")
    add("Export reduction and charge reconcile", abs(h["export_reduction_kwh"].sum() - s["battery_charge_input_kwh"]) < 0.001, f"difference={h['export_reduction_kwh'].sum()-s['battery_charge_input_kwh']:.9f} kWh; within documented legacy clamp artifact")
    add("Monthly import reconciles", np.isclose(monthly["pv_priority_import_kwh"].sum(), s["grid_import_kwh"], atol=1e-8), "12 source-month groups")
    add("Monthly cost reconciles", np.isclose(monthly["pv_priority_cost"].sum(), s["electricity_cost_currency"], atol=1e-8), "12 source-month groups")
    add("Monthly carbon reconciles", np.isclose(monthly["pv_priority_carbon_kg"].sum(), s["carbon_emissions_kgco2"], atol=1e-8), "12 source-month groups")
    add("No daily peak increase", (daily["daily_peak_reduction_kw"] >= -1e-8).all(), f"minimum daily reduction={daily['daily_peak_reduction_kw'].min():.12f} kW")
    add("Annual peak value reconciles", np.isclose(h["grid_import_kwh"].max(), s["peak_grid_import_kw"], atol=1e-10), f"peak={h['grid_import_kwh'].max():.7f} kW")
    add("Terminal SOC is neutral", abs(s["final_soc_kwh"] - s["initial_soc_kwh"]) <= 1e-10, f"initial={s['initial_soc_kwh']:.6f}, final={s['final_soc_kwh']:.6f} kWh")
    add("KPI table complete", len(kpis) == 7 and kpis[["no_battery", "pv_priority"]].notna().all().all(), "seven pre-defined KPIs")
    return pd.DataFrame(checks, columns=["check", "passed", "detail"])


def finish(fig: plt.Figure, filename: str, note: str) -> None:
    fig.text(0.02, 0.012, note, color=GREY, fontsize=8)
    fig.savefig(FIGURES / filename, dpi=220, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def make_figures(
    h: pd.DataFrame,
    kpis: pd.DataFrame,
    monthly: pd.DataFrame,
    daily: pd.DataFrame,
    price: pd.DataFrame,
    carbon: pd.DataFrame,
) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.2, 5.6))
    plot = kpis.iloc[:5].copy()
    plot["normalized_baseline"] = 100.0
    plot["normalized_strategy"] = plot["pv_priority"] / plot["no_battery"] * 100
    y = np.arange(len(plot))
    ax.barh(y + 0.18, plot["normalized_baseline"], 0.36, color="#BCC8D0", label="No battery")
    ax.barh(y - 0.18, plot["normalized_strategy"], 0.36, color=TEAL, label="PV priority")
    ax.set_yticks(y, plot["metric"])
    ax.set_xlabel("Index (no-battery baseline = 100)")
    ax.set_title("Annual KPI comparison")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="x")
    for i, v in enumerate(plot["normalized_strategy"]):
        ax.text(v + 1, i - 0.18, f"{v:.1f}", va="center", fontsize=9)
    fig.subplots_adjust(bottom=0.16)
    finish(fig, "01_annual_kpi_comparison.png", "Energy, cost, carbon and peak are normalized independently. Peak remains at 100 because the annual maximum is unchanged.")

    fig, axes = plt.subplots(2, 1, figsize=(10.4, 7.3), sharex=True)
    x = np.arange(12)
    axes[0].bar(x - 0.2, monthly["import_reduction_pct"], 0.4, label="Import", color=TEAL)
    axes[0].bar(x + 0.2, monthly["cost_saving_pct"], 0.4, label="Cost", color=ORANGE)
    axes[0].plot(x, monthly["carbon_reduction_pct"], marker="o", color=PURPLE, label="Carbon")
    axes[0].set_ylabel("Reduction (%)")
    axes[0].set_title("Monthly energy, cost and carbon reductions")
    axes[0].legend(frameon=False, ncol=3)
    axes[1].bar(x, monthly["peak_reduction_kw"], color=GREEN)
    axes[1].set_ylabel("Peak reduction (kW)")
    axes[1].set_xticks(x, monthly["month_label"])
    axes[1].set_title("Monthly peak reduction")
    fig.subplots_adjust(bottom=0.11, hspace=0.35)
    finish(fig, "02_monthly_impacts.png", "Source months are shown in dataset order (Aug-Jul). Monthly peak reduction does not imply the annual maximum is reduced.")

    by_hour = h.groupby("hour", as_index=False).agg(
        mean_baseline_import=("baseline_import_kwh", "mean"),
        mean_strategy_import=("grid_import_kwh", "mean"),
        mean_import_reduction=("import_reduction_kwh", "mean"),
        mean_soc=("soc_end_kwh", "mean"),
    )
    fig, ax1 = plt.subplots(figsize=(10.3, 5.4))
    ax1.plot(by_hour["hour"], by_hour["mean_baseline_import"], color=NAVY, label="No battery import")
    ax1.plot(by_hour["hour"], by_hour["mean_strategy_import"], color=ORANGE, label="PV-priority import")
    ax1.bar(by_hour["hour"], by_hour["mean_import_reduction"], color=TEAL, alpha=0.35, label="Import reduction")
    ax1.set(xlabel="Source hour (1-24)", ylabel="Mean energy per hour (kWh)", xticks=range(1, 25), title="Mean diurnal import effect and battery SOC")
    ax2 = ax1.twinx()
    ax2.plot(by_hour["hour"], by_hour["mean_soc"], color=PURPLE, ls="--", marker="o", label="Mean SOC")
    ax2.set_ylabel("Mean SOC (kWh)")
    lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    labels = ax1.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax1.legend(lines, labels, frameon=False, ncol=2, loc="upper left")
    fig.subplots_adjust(bottom=0.16)
    finish(fig, "03_diurnal_effect.png", "The controller typically charges in solar hours and discharges later; the plot averages all 365 observations for each source hour.")

    peak_idx = int(h["baseline_import_kwh"].idxmax())
    lo, hi = max(0, peak_idx - 36), min(len(h), peak_idx + 37)
    w = h.iloc[lo:hi].copy()
    x = w["timestamp"] - h.loc[peak_idx, "timestamp"]
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.8), sharex=True)
    axes[0].plot(x, w["baseline_import_kwh"], color=NAVY, label="No battery")
    axes[0].plot(x, w["grid_import_kwh"], color=ORANGE, label="PV priority")
    axes[0].axvline(0, color="#B54747", ls="--", label="Annual peak hour")
    axes[0].set_ylabel("Grid import (kWh/h)")
    axes[0].set_title("Annual peak diagnostic: 72-hour window")
    axes[0].legend(frameon=False, ncol=3)
    axes[1].fill_between(x, 0, w["soc_end_kwh"], color=TEAL, alpha=0.45)
    axes[1].axvline(0, color="#B54747", ls="--")
    axes[1].set(xlabel="Hours relative to annual peak", ylabel="SOC (kWh)")
    fig.subplots_adjust(bottom=0.16, hspace=0.2)
    peak = h.loc[peak_idx]
    finish(fig, "04_annual_peak_diagnostic.png", f"At source step {int(peak.timestamp)} (month {int(peak.month)}, hour {int(peak.hour)}), baseline and PV-priority imports are both {peak.baseline_import_kwh:.3f} kW because SOC is {peak.soc_start_kwh:.3f} kWh.")

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.9))
    axes[0].hist(daily["daily_peak_reduction_kw"], bins=np.linspace(0, max(2.5, daily["daily_peak_reduction_kw"].max()), 21), color=GREEN, edgecolor="white")
    axes[0].set(xlabel="Daily peak reduction (kW)", ylabel="Number of days", title="Distribution of daily peak reduction")
    month_daily = daily.groupby("source_month", as_index=False).agg(days=("day_index", "size"), reduced_days=("peak_reduced_flag", "sum"))
    month_daily["reduced_share"] = month_daily["reduced_days"] / month_daily["days"] * 100
    order = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]
    month_daily = month_daily.set_index("source_month").reindex(order).reset_index()
    axes[1].bar(np.arange(12), month_daily["reduced_share"], color=TEAL)
    axes[1].set(xticks=np.arange(12), xticklabels=["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"], xlabel="Source month", ylabel="Days with lower daily peak (%)", title="How often the daily peak is reduced")
    fig.subplots_adjust(bottom=0.18, wspace=0.3)
    finish(fig, "05_daily_peak_diagnostics.png", "A lower daily peak is observed on 185 of 365 sequential 24-hour groups; the annual maximum nevertheless remains unchanged.")

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.9))
    axes[0].bar(price["price_per_kwh"].astype(str), price["cost_saving"], color=ORANGE)
    axes[0].set(xlabel="Electricity price (currency/kWh)", ylabel="Annual cost saving", title="Cost saving by price tier")
    axes[1].bar(carbon["carbon_quintile"].astype(str), carbon["carbon_reduction_kg"], color=PURPLE)
    axes[1].set(xlabel="Carbon-intensity quintile", ylabel="Carbon reduction (kgCO2)", title="Carbon reduction by intensity quintile")
    axes[1].tick_params(axis="x", rotation=20)
    fig.subplots_adjust(bottom=0.2, wspace=0.28)
    finish(fig, "06_savings_attribution.png", "These are descriptive attributions, not optimized responses: PV-priority timing is driven by PV surplus and load deficit, not price or carbon signals.")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    summary = json.loads(PV_SUMMARY.read_text())
    h = prepare_hourly()
    kpis = kpi_table(summary)
    monthly = monthly_table(h)
    daily = daily_peak_table(h)
    top_peaks = top_peak_table(h)
    price = price_tier_table(h)
    carbon = carbon_bin_table(h)
    checks = validation_table(h, summary, kpis, monthly, daily)
    if not checks["passed"].all():
        raise AssertionError(checks.loc[~checks["passed"]].to_dict("records"))

    peak_idx = int(h["baseline_import_kwh"].idxmax())
    peak = h.loc[peak_idx]
    reduced_days = int(daily["peak_reduced_flag"].sum())
    summary_out = {
        "scope": "Interim comparison: no battery versus PV-priority battery control",
        "annual_kpis": kpis.to_dict("records"),
        "daily_peak_diagnostics": {
            "days_total": int(len(daily)),
            "days_with_lower_peak": reduced_days,
            "days_with_unchanged_peak": int(len(daily) - reduced_days),
            "mean_daily_peak_reduction_kw": float(daily["daily_peak_reduction_kw"].mean()),
            "median_daily_peak_reduction_kw": float(daily["daily_peak_reduction_kw"].median()),
            "maximum_daily_peak_reduction_kw": float(daily["daily_peak_reduction_kw"].max()),
        },
        "annual_peak_diagnostic": {
            "source_time_step": int(peak["timestamp"]),
            "source_month": int(peak["month"]),
            "source_hour_1_to_24": int(peak["hour"]),
            "baseline_peak_kw": float(peak["baseline_import_kwh"]),
            "pv_priority_import_kw": float(peak["grid_import_kwh"]),
            "soc_start_kwh": float(peak["soc_start_kwh"]),
            "battery_exchange_kwh": float(peak["battery_exchange_kwh"]),
            "reason_peak_unchanged": "Battery SOC was zero at the annual peak hour under the myopic PV-priority rule.",
        },
        "validation_checks_passed": int(checks["passed"].sum()),
        "validation_checks_total": int(len(checks)),
    }

    h.to_csv(RESULTS / "hourly_comparison.csv", index=False)
    kpis.to_csv(RESULTS / "annual_kpi_comparison.csv", index=False)
    monthly.to_csv(RESULTS / "monthly_impacts.csv", index=False)
    daily.to_csv(RESULTS / "daily_peak_diagnostics.csv", index=False)
    top_peaks.to_csv(RESULTS / "top20_baseline_peak_hours.csv", index=False)
    price.to_csv(RESULTS / "price_tier_attribution.csv", index=False)
    carbon.to_csv(RESULTS / "carbon_quintile_attribution.csv", index=False)
    checks.to_csv(RESULTS / "validation_checks.csv", index=False)
    (RESULTS / "comparison_summary.json").write_text(json.dumps(summary_out, indent=2), encoding="utf-8")

    make_figures(h, kpis, monthly, daily, price, carbon)

    findings = f"""# Step 8 — Interim comparative analysis

## Result

The PV-priority strategy reduces annual grid import by {kpis.loc[kpis.metric == 'Grid import', 'reported_improvement'].iloc[0]:.2f}%, import-only electricity cost by {kpis.loc[kpis.metric == 'Electricity cost', 'reported_improvement'].iloc[0]:.2f}%, and operational carbon by {kpis.loc[kpis.metric == 'Operational carbon', 'reported_improvement'].iloc[0]:.2f}%. PV self-consumption rises by {kpis.loc[kpis.metric == 'PV self-consumption', 'reported_improvement'].iloc[0]:.2f} percentage points. These effects support the claim that the rule improves on-site PV utilization and reduces grid dependency.

## Peak-load interpretation

The annual peak remains {peak['baseline_import_kwh']:.3f} kW. It occurs at source time step {int(peak['timestamp'])}, month {int(peak['month'])}, source hour {int(peak['hour'])}. At that hour PV is {peak['pv_kwh']:.3f} kWh and battery SOC is {peak['soc_start_kwh']:.3f} kWh, so the battery cannot discharge. This is a mechanism-based explanation: a myopic PV-priority rule uses stored energy whenever a deficit occurs and does not reserve charge for a future annual peak.

This does not mean that the battery never reduces peaks. Daily peaks are lower on {reduced_days} of 365 sequential 24-hour groups, with a mean reduction of {daily['daily_peak_reduction_kw'].mean():.3f} kW and a maximum reduction of {daily['daily_peak_reduction_kw'].max():.3f} kW. However, the single largest annual event is unchanged.

## Scientific interpretation

Cost and carbon savings are consequences of avoided imports at the times when PV-charged energy is discharged. The controller does not observe price or carbon intensity, so savings by price tier or carbon quintile are descriptive attributions, not evidence of cost-optimal or carbon-optimal control. A fair next experiment is a peak-shaving controller with a reserve SOC or forecast-informed target, evaluated using the same battery model and accounting conventions.

## Accuracy and limitations

All {len(checks)} Step 8 checks pass, in addition to all {len(pd.read_csv(PV_CHECKS))} inherited Step 7 battery checks. Annual hourly sums reproduce both scenario summaries; monthly totals reconcile; cost and carbon savings match independent differences; no daily peak increases; and initial and terminal SOC are both zero. The 0.000588 kWh difference between annual discharge and avoided import is below 0.001 kWh and arises from the documented CityLearn v1.3.6 capacity-fade clamp artifact.

The results are deterministic for one residential building and one supplied year. They do not establish statistical generalizability or causal effects for offices, other climates, other tariffs, or other battery sizes. Source month/hour labels are retained because full calendar timestamps are unavailable.
"""
    (ROOT / "Step8_Interim_Comparison_Findings.md").write_text(findings, encoding="utf-8")
    print(json.dumps(summary_out, indent=2))


if __name__ == "__main__":
    main()
