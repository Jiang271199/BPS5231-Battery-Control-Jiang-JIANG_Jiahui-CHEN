"""Step 6: reproducible no-battery baseline for CityLearn 2022 Building_5.

This is deterministic hourly accounting, not a CityLearn battery simulation.
The building retains its 4 kW PV system, while battery charge/discharge is zero.
Imports incur the supplied tariff and grid carbon intensity; exports receive no
financial payment and no carbon credit in the primary baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data" / "processed" / "building_5_hourly_inputs.csv"
RESULTS = ROOT / "results" / "baseline"
FIGURES = ROOT / "figures" / "baseline"
RESULTS.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

NAVY = "#14334D"
TEAL = "#087E8B"
ORANGE = "#DE7B36"
PURPLE = "#77559B"
GREEN = "#4B8C67"
GREY = "#687682"

plt.rcParams.update({
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
})


def audit_input(df: pd.DataFrame) -> None:
    required = [
        "time_step", "month_source", "hour_source_1_to_24", "day_type_source",
        "load_kwh_step", "pv_generation_kwh_step",
        "electricity_price_currency_per_kwh", "carbon_intensity_kgco2_per_kwh",
    ]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Required baseline columns missing: {sorted(missing)}")
    if len(df) != 8760 or not np.array_equal(df.time_step.to_numpy(), np.arange(8760)):
        raise ValueError("Expected exactly 8,760 sequential hourly records")
    if df[required].isna().any().any():
        raise ValueError("Missing values in required baseline columns")
    numeric = [
        "load_kwh_step", "pv_generation_kwh_step",
        "electricity_price_currency_per_kwh", "carbon_intensity_kgco2_per_kwh",
    ]
    if (df[numeric] < 0).any().any():
        raise ValueError("Negative load, PV, price or carbon intensity")


def calculate(df: pd.DataFrame) -> pd.DataFrame:
    out = df[[
        "time_step", "month_source", "hour_source_1_to_24", "day_type_source",
        "load_kwh_step", "pv_generation_kwh_step",
        "electricity_price_currency_per_kwh", "carbon_intensity_kgco2_per_kwh",
    ]].copy()
    out["battery_charge_kwh_step"] = 0.0
    out["battery_discharge_kwh_step"] = 0.0
    out["battery_throughput_kwh_step"] = 0.0
    out["direct_pv_use_kwh_step"] = np.minimum(out.load_kwh_step, out.pv_generation_kwh_step)
    out["grid_exchange_kwh_step"] = out.load_kwh_step - out.pv_generation_kwh_step
    out["grid_import_kwh_step"] = out.grid_exchange_kwh_step.clip(lower=0.0)
    out["grid_export_kwh_step"] = (-out.grid_exchange_kwh_step).clip(lower=0.0)
    out["electricity_cost_currency_step"] = (
        out.grid_import_kwh_step * out.electricity_price_currency_per_kwh
    )
    out["operational_carbon_kgco2_step"] = (
        out.grid_import_kwh_step * out.carbon_intensity_kgco2_per_kwh
    )
    out["no_pv_cost_currency_step"] = out.load_kwh_step * out.electricity_price_currency_per_kwh
    out["no_pv_carbon_kgco2_step"] = out.load_kwh_step * out.carbon_intensity_kgco2_per_kwh
    return out


def verify_hourly(df: pd.DataFrame) -> None:
    checks = {
        "load balance": df.load_kwh_step - (df.direct_pv_use_kwh_step + df.grid_import_kwh_step),
        "PV balance": df.pv_generation_kwh_step - (df.direct_pv_use_kwh_step + df.grid_export_kwh_step),
        "grid exchange": df.grid_exchange_kwh_step - (df.grid_import_kwh_step - df.grid_export_kwh_step),
    }
    for label, residual in checks.items():
        if not np.allclose(residual, 0.0, atol=1e-10):
            raise AssertionError(f"Hourly {label} failed: max residual={abs(residual).max()}")
    if (df.grid_import_kwh_step.gt(0) & df.grid_export_kwh_step.gt(0)).any():
        raise AssertionError("Simultaneous grid import and export in no-battery baseline")
    if not (df[["battery_charge_kwh_step", "battery_discharge_kwh_step", "battery_throughput_kwh_step"]] == 0).all().all():
        raise AssertionError("Battery activity must be exactly zero")


def aggregate(df: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    load = float(df.load_kwh_step.sum())
    pv = float(df.pv_generation_kwh_step.sum())
    direct_pv = float(df.direct_pv_use_kwh_step.sum())
    grid_import = float(df.grid_import_kwh_step.sum())
    grid_export = float(df.grid_export_kwh_step.sum())
    cost = float(df.electricity_cost_currency_step.sum())
    carbon = float(df.operational_carbon_kgco2_step.sum())
    no_pv_cost = float(df.no_pv_cost_currency_step.sum())
    no_pv_carbon = float(df.no_pv_carbon_kgco2_step.sum())
    peak_idx = int(df.grid_import_kwh_step.idxmax())

    summary = {
        "scenario": "PV system active; battery charge and discharge fixed at zero",
        "calculation_type": "Deterministic hourly accounting; not a CityLearn engine run",
        "rows": len(df),
        "time_step_hours": 1,
        "annual_load_kwh": load,
        "annual_pv_generation_kwh": pv,
        "annual_direct_pv_use_kwh": direct_pv,
        "annual_grid_import_kwh": grid_import,
        "annual_grid_export_kwh": grid_export,
        "annual_net_grid_exchange_kwh": grid_import - grid_export,
        "annual_electricity_cost_currency": cost,
        "annual_operational_carbon_kgco2": carbon,
        "pv_self_consumption_ratio": direct_pv / pv,
        "pv_export_ratio": grid_export / pv,
        "pv_self_sufficiency_ratio": direct_pv / load,
        "grid_import_share_of_load": grid_import / load,
        "peak_hourly_average_grid_import_kw": float(df.grid_import_kwh_step.max()),
        "peak_import_time_step": int(df.loc[peak_idx, "time_step"]),
        "peak_import_source_month": int(df.loc[peak_idx, "month_source"]),
        "peak_import_source_hour_1_to_24": int(df.loc[peak_idx, "hour_source_1_to_24"]),
        "import_weighted_mean_price_currency_per_kwh": cost / grid_import,
        "import_weighted_mean_carbon_kgco2_per_kwh": carbon / grid_import,
        "counterfactual_no_pv_cost_currency": no_pv_cost,
        "counterfactual_no_pv_carbon_kgco2": no_pv_carbon,
        "pv_avoided_import_cost_currency": no_pv_cost - cost,
        "pv_avoided_import_carbon_kgco2": no_pv_carbon - carbon,
        "battery_charge_kwh": 0.0,
        "battery_discharge_kwh": 0.0,
        "battery_throughput_kwh": 0.0,
        "export_payment_currency": 0.0,
        "export_carbon_credit_kgco2": 0.0,
        "no_full_timestamps": True,
    }

    order = list(range(8, 13)) + list(range(1, 8))
    monthly = df.groupby("month_source", sort=False).agg(
        hours=("time_step", "size"),
        load_kwh=("load_kwh_step", "sum"),
        pv_generation_kwh=("pv_generation_kwh_step", "sum"),
        direct_pv_use_kwh=("direct_pv_use_kwh_step", "sum"),
        grid_import_kwh=("grid_import_kwh_step", "sum"),
        grid_export_kwh=("grid_export_kwh_step", "sum"),
        peak_hourly_average_grid_import_kw=("grid_import_kwh_step", "max"),
        electricity_cost_currency=("electricity_cost_currency_step", "sum"),
        operational_carbon_kgco2=("operational_carbon_kgco2_step", "sum"),
    ).reindex(order)
    monthly.insert(0, "month", monthly.index)
    monthly["pv_self_consumption_ratio"] = monthly.direct_pv_use_kwh / monthly.pv_generation_kwh
    monthly["pv_self_sufficiency_ratio"] = monthly.direct_pv_use_kwh / monthly.load_kwh
    monthly = monthly.reset_index(drop=True)

    hourly = df.groupby("hour_source_1_to_24", sort=True).agg(
        observations=("time_step", "size"),
        mean_load_kwh_step=("load_kwh_step", "mean"),
        mean_pv_generation_kwh_step=("pv_generation_kwh_step", "mean"),
        mean_direct_pv_use_kwh_step=("direct_pv_use_kwh_step", "mean"),
        mean_grid_import_kwh_step=("grid_import_kwh_step", "mean"),
        mean_grid_export_kwh_step=("grid_export_kwh_step", "mean"),
        annual_grid_import_kwh=("grid_import_kwh_step", "sum"),
        annual_grid_export_kwh=("grid_export_kwh_step", "sum"),
        annual_cost_currency=("electricity_cost_currency_step", "sum"),
        annual_carbon_kgco2=("operational_carbon_kgco2_step", "sum"),
    ).reset_index()

    price_tier = df.groupby("electricity_price_currency_per_kwh", sort=True).agg(
        hours=("time_step", "size"),
        grid_import_kwh=("grid_import_kwh_step", "sum"),
        electricity_cost_currency=("electricity_cost_currency_step", "sum"),
        operational_carbon_kgco2=("operational_carbon_kgco2_step", "sum"),
    ).reset_index()
    price_tier["share_of_annual_import"] = price_tier.grid_import_kwh / grid_import
    price_tier["share_of_annual_cost"] = price_tier.electricity_cost_currency / cost

    # Annual and monthly identities must reconcile independently.
    if not np.isclose(load, direct_pv + grid_import, atol=1e-7):
        raise AssertionError("Annual load balance failed")
    if not np.isclose(pv, direct_pv + grid_export, atol=1e-7):
        raise AssertionError("Annual PV balance failed")
    for column, annual in [
        ("load_kwh", load), ("pv_generation_kwh", pv), ("direct_pv_use_kwh", direct_pv),
        ("grid_import_kwh", grid_import), ("grid_export_kwh", grid_export),
        ("electricity_cost_currency", cost), ("operational_carbon_kgco2", carbon),
    ]:
        if not np.isclose(float(monthly[column].sum()), annual, atol=1e-7):
            raise AssertionError(f"Monthly reconciliation failed: {column}")
    if not np.isclose(float(price_tier.electricity_cost_currency.sum()), cost, atol=1e-7):
        raise AssertionError("Price-tier cost reconciliation failed")
    return summary, monthly, hourly, price_tier


def finish(fig: plt.Figure, filename: str, note: str) -> None:
    fig.text(0.02, 0.015, note, color=GREY, fontsize=8)
    fig.savefig(FIGURES / filename, dpi=220, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def figure_selected_period(df: pd.DataFrame) -> None:
    sample = df.iloc[1:169]
    x = np.arange(len(sample)) / 24
    net = sample.grid_exchange_kwh_step.to_numpy()
    fig, ax = plt.subplots(figsize=(10.2, 4.9))
    ax.fill_between(x, 0, np.maximum(net, 0), color=ORANGE, alpha=0.42, label="Grid import")
    ax.fill_between(x, 0, np.minimum(net, 0), color=TEAL, alpha=0.42, label="Grid export")
    ax.plot(x, net, color=NAVY, lw=1.35, label="Net grid exchange")
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set(xlim=(0, 7), xlabel="Day within selected period", ylabel="Energy per hour (kWh)",
           title="No-battery grid exchange: selected 168-hour period")
    ax.set_xticks(range(0, 8))
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=3, loc="upper right")
    fig.subplots_adjust(bottom=0.17)
    finish(fig, "01_baseline_selected_period.png",
           "CityLearn 2022, Building_5, source steps 1-168. Positive values are imports; negative values are exports.")


def figure_monthly(monthly: pd.DataFrame) -> None:
    labels = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    x = np.arange(12)
    fig, axes = plt.subplots(2, 2, figsize=(10.4, 7.0), sharex=True)
    axes[0, 0].bar(x - .2, monthly.grid_import_kwh, .4, color=ORANGE, label="Import")
    axes[0, 0].bar(x + .2, monthly.grid_export_kwh, .4, color=TEAL, label="Export")
    axes[0, 0].set(title="Grid import and export", ylabel="Energy (kWh)")
    axes[0, 0].legend(frameon=False, ncol=2)
    axes[0, 1].bar(x, monthly.electricity_cost_currency, color=PURPLE)
    axes[0, 1].set(title="Import-only electricity cost", ylabel="Currency")
    axes[1, 0].bar(x, monthly.operational_carbon_kgco2, color=GREEN)
    axes[1, 0].set(title="Import-only operational carbon", ylabel="kgCO2")
    axes[1, 1].plot(x, monthly.peak_hourly_average_grid_import_kw, color=NAVY, marker="o", lw=1.8)
    axes[1, 1].set(title="Hourly-average grid import peak", ylabel="kW")
    for ax in axes.flat:
        ax.grid(axis="y")
        ax.set_axisbelow(True)
        ax.set_xticks(x, labels, rotation=0)
    fig.tight_layout(rect=(0, .05, 1, 1))
    finish(fig, "02_baseline_monthly_kpis.png",
           "CityLearn 2022, Building_5. Study-year order is August-July; exports receive no payment or carbon credit.")


def figure_cumulative(df: pd.DataFrame, summary: dict[str, object]) -> None:
    x = np.arange(len(df)) / 24
    fig, axes = plt.subplots(2, 1, figsize=(10.1, 6.0), sharex=True)
    axes[0].plot(x, df.electricity_cost_currency_step.cumsum(), color=PURPLE, lw=1.8)
    axes[0].set(title="Cumulative no-battery electricity cost", ylabel="Currency")
    axes[0].text(.99, .05, f"Annual total = {summary['annual_electricity_cost_currency']:.2f}",
                 transform=axes[0].transAxes, ha="right", color=PURPLE)
    axes[1].plot(x, df.operational_carbon_kgco2_step.cumsum(), color=GREEN, lw=1.8)
    axes[1].set(xlabel="Elapsed day in study year", ylabel="kgCO2",
                title="Cumulative no-battery operational carbon")
    axes[1].text(.99, .05, f"Annual total = {summary['annual_operational_carbon_kgco2']:.2f} kgCO2",
                 transform=axes[1].transAxes, ha="right", color=GREEN)
    for ax in axes:
        ax.grid(axis="y")
    fig.tight_layout(rect=(0, .05, 1, 1))
    finish(fig, "03_baseline_cumulative_cost_carbon.png",
           "Primary accounting uses grid imports only. No export tariff or export carbon credit is applied.")


def figure_diurnal(hourly: pd.DataFrame) -> None:
    x = hourly.hour_source_1_to_24.to_numpy()
    fig, axes = plt.subplots(2, 1, figsize=(9.6, 6.3), sharex=True)
    axes[0].plot(x, hourly.mean_direct_pv_use_kwh_step, color=GREEN, lw=2, label="Direct PV use")
    axes[0].plot(x, hourly.mean_grid_import_kwh_step, color=ORANGE, lw=2, label="Grid import")
    axes[0].plot(x, hourly.mean_grid_export_kwh_step, color=TEAL, lw=2, label="Grid export")
    axes[0].set(title="Mean hourly energy balance", ylabel="Mean energy per hour (kWh)")
    axes[0].legend(frameon=False, ncol=3)
    width = .38
    axes[1].bar(x - width/2, hourly.annual_cost_currency, width, color=PURPLE, label="Cost")
    ax2 = axes[1].twinx()
    ax2.bar(x + width/2, hourly.annual_carbon_kgco2, width, color=GREEN, alpha=.85, label="Carbon")
    axes[1].set(ylabel="Annual cost by source hour (currency)", xlabel="Source hour label (1-24)")
    ax2.set_ylabel("Annual carbon by source hour (kgCO2)", color=GREEN)
    axes[1].set_xticks([1, 4, 8, 12, 16, 20, 24])
    axes[1].legend(frameon=False, loc="upper left")
    ax2.legend(frameon=False, loc="upper right")
    for ax in axes:
        ax.grid(axis="y")
    fig.tight_layout(rect=(0, .05, 1, 1))
    finish(fig, "04_baseline_diurnal_contributions.png",
           "Each source-hour bin contains 365 observations. Cost and carbon use imported electricity only.")


def main() -> None:
    raw = pd.read_csv(INPUT)
    audit_input(raw)
    baseline = calculate(raw)
    verify_hourly(baseline)
    summary, monthly, hourly, price_tier = aggregate(baseline)

    baseline.to_csv(RESULTS / "hourly_no_battery_baseline.csv", index=False, float_format="%.10g")
    monthly.to_csv(RESULTS / "monthly_no_battery_baseline.csv", index=False, float_format="%.10g")
    hourly.to_csv(RESULTS / "hourly_clock_no_battery_baseline.csv", index=False, float_format="%.10g")
    price_tier.to_csv(RESULTS / "price_tier_no_battery_baseline.csv", index=False, float_format="%.10g")
    pd.DataFrame([
        {"metric": key, "value": value}
        for key, value in summary.items()
        if isinstance(value, (int, float, bool))
    ]).to_csv(RESULTS / "baseline_kpis.csv", index=False)
    (RESULTS / "baseline_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    figure_selected_period(baseline)
    figure_monthly(monthly)
    figure_cumulative(baseline, summary)
    figure_diurnal(hourly)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
