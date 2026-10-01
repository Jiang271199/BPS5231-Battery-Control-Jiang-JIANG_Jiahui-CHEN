"""Reproducible exploratory analysis for CityLearn 2022 Building_5.

Outputs descriptive figures and tables only. No battery controller is simulated.
Run with the bundled Python runtime or a Python environment containing pandas,
numpy and matplotlib:

    python 05_exploratory_data_analysis.py
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
FIGURES = ROOT / "figures" / "eda"
TABLES = ROOT / "results" / "eda"
FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

NAVY = "#14334D"
TEAL = "#087E8B"
ORANGE = "#DE7B36"
PURPLE = "#77559B"
GREY = "#687682"
GREEN = "#4B8C67"

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


def finish(fig: plt.Figure, path: Path, note: str) -> None:
    fig.text(0.02, 0.017, note, color=GREY, fontsize=8)
    fig.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def audit_inputs(df: pd.DataFrame) -> None:
    required = [
        "time_step", "month_source", "hour_source_1_to_24", "day_type_source",
        "load_kwh_step", "pv_generation_kwh_step",
        "electricity_price_currency_per_kwh", "carbon_intensity_kgco2_per_kwh",
    ]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Required EDA columns missing: {sorted(missing)}")
    if len(df) != 8760 or not np.array_equal(df.time_step.to_numpy(), np.arange(8760)):
        raise ValueError("Expected exactly 8,760 sequential hourly rows")
    if df[required].isna().any().any():
        raise ValueError("Missing values in required EDA columns")
    if (df[["load_kwh_step", "pv_generation_kwh_step", "electricity_price_currency_per_kwh", "carbon_intensity_kgco2_per_kwh"]] < 0).any().any():
        raise ValueError("Negative load, PV, price or carbon intensity")


def save_data(df: pd.DataFrame) -> dict[str, object]:
    load = df.load_kwh_step
    pv = df.pv_generation_kwh_step
    net = df.net_before_battery_kwh_step
    positive = net.clip(lower=0)
    surplus = (-net).clip(lower=0)

    order = list(range(8, 13)) + list(range(1, 8))
    monthly = df.groupby("month_source", sort=False).agg(
        hours=("time_step", "size"),
        load_kwh=("load_kwh_step", "sum"),
        pv_generation_kwh=("pv_generation_kwh_step", "sum"),
        potential_surplus_kwh=("pv_surplus_kwh_step", "sum"),
        peak_import_before_battery_kw=("net_before_battery_kwh_step", "max"),
    ).reindex(order)
    monthly.insert(0, "month", monthly.index)
    monthly.reset_index(drop=True).to_csv(TABLES / "monthly_summary.csv", index=False, float_format="%.10g")

    by_hour = df.groupby("hour_source_1_to_24", sort=True).agg(
        n=("time_step", "size"),
        load_mean_kwh_step=("load_kwh_step", "mean"),
        load_p10_kwh_step=("load_kwh_step", lambda x: x.quantile(0.1)),
        load_p90_kwh_step=("load_kwh_step", lambda x: x.quantile(0.9)),
        pv_mean_kwh_step=("pv_generation_kwh_step", "mean"),
        pv_p10_kwh_step=("pv_generation_kwh_step", lambda x: x.quantile(0.1)),
        pv_p90_kwh_step=("pv_generation_kwh_step", lambda x: x.quantile(0.9)),
        surplus_hours=("pv_surplus_kwh_step", lambda x: int((x > 0).sum())),
        surplus_kwh=("pv_surplus_kwh_step", "sum"),
    ).reset_index()
    by_hour.to_csv(TABLES / "hourly_profile.csv", index=False, float_format="%.10g")

    price_carbon = df.groupby("electricity_price_currency_per_kwh", sort=True).agg(
        n=("time_step", "size"),
        carbon_mean_kgco2_per_kwh=("carbon_intensity_kgco2_per_kwh", "mean"),
        carbon_median_kgco2_per_kwh=("carbon_intensity_kgco2_per_kwh", "median"),
        carbon_p10_kgco2_per_kwh=("carbon_intensity_kgco2_per_kwh", lambda x: x.quantile(0.1)),
        carbon_p90_kgco2_per_kwh=("carbon_intensity_kgco2_per_kwh", lambda x: x.quantile(0.9)),
    ).reset_index()
    price_carbon.to_csv(TABLES / "price_carbon_by_tariff.csv", index=False, float_format="%.10g")

    peak_threshold = float(positive.quantile(0.99))
    peak_mask = positive >= peak_threshold
    peak_by_hour = df.loc[peak_mask].groupby("hour_source_1_to_24").size().reindex(range(1, 25), fill_value=0)
    peak_by_hour.rename("top_1pct_import_hour_count").rename_axis("hour_source_1_to_24").reset_index().to_csv(
        TABLES / "peak_hours_by_hour.csv", index=False
    )

    if not np.isclose(load.sum() - pv.sum(), net.sum(), atol=1e-7):
        raise AssertionError("Annual energy balance failed")
    if not np.isclose(positive.sum() - surplus.sum(), net.sum(), atol=1e-7):
        raise AssertionError("Import/surplus balance failed")
    if not np.isclose(monthly.load_kwh.sum(), load.sum(), atol=1e-7):
        raise AssertionError("Monthly load reconciliation failed")
    if not np.isclose(monthly.pv_generation_kwh.sum(), pv.sum(), atol=1e-7):
        raise AssertionError("Monthly PV reconciliation failed")
    if not np.isclose(monthly.potential_surplus_kwh.sum(), surplus.sum(), atol=1e-7):
        raise AssertionError("Monthly surplus reconciliation failed")
    if int(peak_by_hour.sum()) != int(peak_mask.sum()):
        raise AssertionError("Peak hour counts do not reconcile")

    summary = {
        "scope": "Exploratory statistics only; no battery simulation",
        "rows": len(df),
        "hours_per_clock_hour": df.hour_source_1_to_24.value_counts().sort_index().tolist(),
        "annual_load_kwh": float(load.sum()),
        "annual_pv_generation_kwh": float(pv.sum()),
        "annual_net_exchange_before_battery_kwh": float(net.sum()),
        "potential_grid_import_before_battery_kwh": float(positive.sum()),
        "potential_pv_surplus_before_battery_kwh": float(surplus.sum()),
        "potential_pv_surplus_hours": int((surplus > 0).sum()),
        "potential_grid_import_hours": int((net > 0).sum()),
        "zero_net_exchange_hours": int((net == 0).sum()),
        "peak_load_kwh_in_hour": float(load.max()),
        "peak_import_before_battery_kw": float(positive.max()),
        "peak_import_top_1pct_threshold_kw": peak_threshold,
        "peak_import_top_1pct_hours": int(peak_mask.sum()),
        "load_p50_kwh_step": float(load.median()),
        "load_p90_kwh_step": float(load.quantile(0.90)),
        "pv_nonzero_hours": int((pv > 0).sum()),
        "price_levels": sorted(float(x) for x in df.electricity_price_currency_per_kwh.unique()),
        "price_carbon_pearson_r": float(df.electricity_price_currency_per_kwh.corr(df.carbon_intensity_kgco2_per_kwh, method="pearson")),
        "price_carbon_spearman_r": float(df.electricity_price_currency_per_kwh.corr(df.carbon_intensity_kgco2_per_kwh, method="spearman")),
        "highest_monthly_load_month": int(monthly.loc[monthly.load_kwh.idxmax(), "month"]),
        "highest_monthly_load_kwh": float(monthly.load_kwh.max()),
        "highest_monthly_pv_month": int(monthly.loc[monthly.pv_generation_kwh.idxmax(), "month"]),
        "highest_monthly_pv_kwh": float(monthly.pv_generation_kwh.max()),
        "highest_monthly_surplus_month": int(monthly.loc[monthly.potential_surplus_kwh.idxmax(), "month"]),
        "highest_monthly_surplus_kwh": float(monthly.potential_surplus_kwh.max()),
        "top_peak_hours": [int(x) for x in peak_by_hour.sort_values(ascending=False).head(3).index],
        "selected_period_source_time_steps": [1, 168],
        "no_full_timestamps": True,
    }
    (TABLES / "eda_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def figure_week(df: pd.DataFrame) -> None:
    sample = df.iloc[1:169]
    x = np.arange(len(sample))
    fig, ax = plt.subplots(figsize=(10, 4.9))
    ax.plot(x, sample.load_kwh_step, color=NAVY, lw=1.55, label="Building electricity load")
    ax.plot(x, sample.pv_generation_kwh_step, color=ORANGE, lw=1.5, label="PV generation")
    ax.plot(x, sample.net_before_battery_kwh_step, color=TEAL, lw=1.1, alpha=0.82, label="Net grid exchange")
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set(xlim=(0, 167), xlabel="Hours from start of selected 168-hour period", ylabel="Energy per hour (kWh)",
           title="Building load, PV and net exchange: first complete 168-hour period")
    ax.set_xticks(range(0, 169, 24))
    ax.set_xticklabels([str(x // 24) for x in range(0, 169, 24)])
    ax.set_xlabel("Day within selected period")
    ax.grid(axis="y")
    ax.legend(loc="upper right", frameon=False, ncol=3, fontsize=8.3)
    fig.subplots_adjust(bottom=0.17)
    finish(fig, FIGURES / "01_selected_week_load_pv_net.png",
           "CityLearn 2022, Building_5. Source steps 1-168. Negative net exchange indicates potential export before battery.")


def figure_diurnal(df: pd.DataFrame) -> None:
    hourly = pd.read_csv(TABLES / "hourly_profile.csv")
    x = hourly.hour_source_1_to_24.to_numpy()
    fig, ax = plt.subplots(figsize=(9.4, 5.0))
    ax.fill_between(x, hourly.load_p10_kwh_step, hourly.load_p90_kwh_step, color=NAVY, alpha=0.12)
    ax.fill_between(x, hourly.pv_p10_kwh_step, hourly.pv_p90_kwh_step, color=ORANGE, alpha=0.15)
    ax.plot(x, hourly.load_mean_kwh_step, color=NAVY, lw=2.1, label="Load mean (10th-90th percentile band)")
    ax.plot(x, hourly.pv_mean_kwh_step, color=ORANGE, lw=2.1, label="PV mean (10th-90th percentile band)")
    ax.set(xlim=(1, 24), xticks=[1, 4, 8, 12, 16, 20, 24], xlabel="Source hour label (1-24)",
           ylabel="Energy per hour (kWh)", title="Diurnal load and PV profiles across 365 days")
    ax.grid(axis="y")
    ax.legend(frameon=False, fontsize=8.8)
    fig.subplots_adjust(bottom=0.17)
    finish(fig, FIGURES / "02_diurnal_load_pv.png",
           "CityLearn 2022, Building_5. Bands show hourly 10th-90th percentiles, not uncertainty intervals for the mean.")


def figure_monthly(df: pd.DataFrame) -> None:
    monthly = pd.read_csv(TABLES / "monthly_summary.csv")
    labels = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    x = np.arange(12)
    fig, axes = plt.subplots(2, 1, figsize=(9.6, 6.5), sharex=True, gridspec_kw={"height_ratios": [2.1, 1.25]})
    width = 0.37
    axes[0].bar(x - width/2, monthly.load_kwh, width, color=NAVY, label="Building load")
    axes[0].bar(x + width/2, monthly.pv_generation_kwh, width, color=ORANGE, label="PV generation")
    axes[0].set(ylabel="Monthly energy (kWh)", title="Monthly load, PV and potential surplus")
    axes[0].legend(frameon=False, ncol=2)
    axes[0].grid(axis="y")
    axes[0].set_axisbelow(True)
    axes[1].bar(x, monthly.potential_surplus_kwh, color=TEAL)
    axes[1].set(ylabel="Potential PV surplus (kWh)", xlabel="Source month, study-year order")
    axes[1].grid(axis="y")
    axes[1].set_axisbelow(True)
    axes[1].set_xticks(x, labels)
    fig.tight_layout(rect=(0, .035, 1, 1))
    finish(fig, FIGURES / "03_monthly_energy_surplus.png",
           "CityLearn 2022, Building_5. Potential surplus = sum[max(PV - load, 0)] before battery. Month follows source labels.")


def figure_signals(df: pd.DataFrame) -> None:
    sample = df.iloc[1:169]
    x = np.arange(len(sample)) / 24
    fig, axes = plt.subplots(2, 1, figsize=(9.6, 5.8), sharex=True)
    axes[0].step(x, sample.electricity_price_currency_per_kwh, where="mid", color=PURPLE, lw=1.45)
    axes[0].set(ylabel="Price (currency/kWh)", title="Price and grid carbon intensity over the same 168-hour period")
    axes[1].plot(x, sample.carbon_intensity_kgco2_per_kwh, color=GREEN, lw=1.55)
    axes[1].set(ylabel="Carbon intensity (kgCO2/kWh)", xlabel="Day within selected period")
    axes[1].set_xticks(np.arange(0, 8, 1))
    for ax in axes:
        ax.grid(axis="y")
    fig.tight_layout(rect=(0, .04, 1, 1))
    finish(fig, FIGURES / "04_price_carbon_selected_week.png",
           "CityLearn 2022. Source steps 1-168. Same-row alignment is supplied by the dataset; no full timestamps are available.")


def figure_price_carbon(df: pd.DataFrame, summary: dict[str, object]) -> None:
    tiers = sorted(df.electricity_price_currency_per_kwh.unique())
    groups = [df.loc[df.electricity_price_currency_per_kwh == tier, "carbon_intensity_kgco2_per_kwh"].to_numpy() for tier in tiers]
    fig, ax = plt.subplots(figsize=(9.1, 5.1))
    b = ax.boxplot(groups, positions=np.arange(len(tiers)), widths=0.58, patch_artist=True,
                   showfliers=False, medianprops={"color": NAVY, "linewidth": 1.7})
    for box in b["boxes"]:
        box.set_facecolor("#C5E2E2")
        box.set_edgecolor(TEAL)
    for item in b["whiskers"] + b["caps"]:
        item.set_color(TEAL)
    ax.set_xticks(np.arange(len(tiers)), [f"{tier:.2f}\n(n={len(group):,})" for tier, group in zip(tiers, groups)])
    ax.set(xlabel="Electricity price tier (currency/kWh)", ylabel="Carbon intensity (kgCO2/kWh)",
           title="Grid carbon intensity at each electricity price tier")
    ax.text(.98, .97, f"Pearson r = {summary['price_carbon_pearson_r']:.3f}\nSpearman r = {summary['price_carbon_spearman_r']:.3f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=NAVY,
            bbox={"facecolor": "white", "edgecolor": "#DCE3E8", "boxstyle": "round,pad=0.45"})
    ax.grid(axis="y")
    fig.subplots_adjust(bottom=0.25)
    finish(fig, FIGURES / "05_price_carbon_by_tariff.png",
           "CityLearn 2022, 8,760 hours. Boxes: median and IQR; whiskers: 1.5x IQR; outliers hidden. Correlation is descriptive.")


def figure_surplus(df: pd.DataFrame) -> None:
    hourly = pd.read_csv(TABLES / "hourly_profile.csv")
    x = hourly.hour_source_1_to_24.to_numpy()
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.1), sharex=True)
    axes[0].bar(x, hourly.surplus_hours, color=TEAL, width=.82)
    axes[0].set(ylabel="Hours with PV > load", title="When potential PV surplus occurs")
    axes[1].bar(x, hourly.surplus_kwh, color=ORANGE, width=.82)
    axes[1].set(ylabel="Annual surplus by source hour (kWh)", xlabel="Source hour label (1-24)")
    axes[1].set_xticks([1, 4, 8, 12, 16, 20, 24])
    for ax in axes:
        ax.grid(axis="y")
        ax.set_axisbelow(True)
    fig.tight_layout(rect=(0, .04, 1, 1))
    finish(fig, FIGURES / "06_pv_surplus_opportunity.png",
           "CityLearn 2022, Building_5. Surplus is max(PV - load, 0) before storage; this is an opportunity, not realised self-consumption.")


def figure_peak(df: pd.DataFrame, summary: dict[str, object]) -> None:
    peak = pd.read_csv(TABLES / "peak_hours_by_hour.csv")
    positive = df.net_before_battery_kwh_step.clip(lower=0).to_numpy()
    ordered = np.sort(positive)[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.8), gridspec_kw={"width_ratios": [1.35, 1]})
    axes[0].plot(np.arange(1, len(ordered)+1), ordered, color=NAVY, lw=1.65)
    axes[0].axhline(summary["peak_import_top_1pct_threshold_kw"], color=ORANGE, lw=1.1, ls="--",
                    label=f"99th percentile = {summary['peak_import_top_1pct_threshold_kw']:.2f} kW")
    axes[0].set(xlabel="Ranked hour (descending)", ylabel="Potential grid import (kW)",
                title="Pre-battery import duration curve")
    axes[0].legend(frameon=False, fontsize=8.5)
    axes[1].bar(peak.hour_source_1_to_24, peak.top_1pct_import_hour_count, color=PURPLE, width=.83)
    axes[1].set(xlabel="Source hour label (1-24)", ylabel="Count of top 1% hours",
                title="Timing of highest import hours")
    axes[1].set_xticks([1, 4, 8, 12, 16, 20, 24])
    for ax in axes:
        ax.grid(axis="y")
        ax.set_axisbelow(True)
    fig.tight_layout(rect=(0, .06, 1, 1))
    finish(fig, FIGURES / "07_import_peaks_before_battery.png",
           "CityLearn 2022, Building_5. Potential import = max(load - PV, 0). Top 1% threshold computed on all 8,760 hours.")


def main() -> None:
    df = pd.read_csv(INPUT)
    audit_inputs(df)
    df["net_before_battery_kwh_step"] = df.load_kwh_step - df.pv_generation_kwh_step
    df["pv_surplus_kwh_step"] = (-df.net_before_battery_kwh_step).clip(lower=0)
    summary = save_data(df)
    figure_week(df)
    figure_diurnal(df)
    figure_monthly(df)
    figure_signals(df)
    figure_price_carbon(df, summary)
    figure_surplus(df)
    figure_peak(df, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
