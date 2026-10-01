#!/usr/bin/env python3
"""Step 7: PV-priority battery control for Building_5.

The battery equations reproduce the relevant CityLearn v1.3.6 Battery and
StorageDevice logic using parameters in the local 2021 schema. The controller
is deliberately rule-based: charge only from contemporaneous PV surplus and
discharge only to meet contemporaneous building deficit.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "processed" / "building_5_hourly_inputs.csv"
SCHEMA_FILE = ROOT / "data" / "raw" / "schema.json"
BASELINE_SUMMARY = ROOT / "results" / "baseline" / "baseline_summary.json"
RESULTS = ROOT / "results" / "pv_priority"
FIGURES = ROOT / "figures" / "pv_priority"

CITYLEARN_SOURCE = (
    "https://github.com/intelligent-environments-lab/CityLearn/blob/"
    "v1.3.6/citylearn/energy_model.py"
)


def legacy_linear_interpolation(x: float, curve: np.ndarray) -> float:
    """Match CityLearn v1.3.6's curve indexing/interpolation convention."""
    index = max(0, int(np.argmax(x <= curve[:, 0])) - 1)
    x0, y0 = curve[index]
    x1, y1 = curve[index + 1]
    slope = (y1 - y0) / (x1 - x0)
    return float(y0 + slope * (x - x0))


def run_battery_controller(df: pd.DataFrame, battery: dict) -> pd.DataFrame:
    initial_capacity = float(battery["capacity"])
    nominal_power = float(battery["nominal_power"])
    loss_coefficient = float(battery.get("loss_coefficient", 0.006))
    capacity_loss_coefficient = float(
        battery.get("capacity_loss_coefficient", 1.0e-5)
    )
    efficiency_scaling = 0.5

    # These are the CityLearn v1.3.6 Battery defaults when not in schema.json.
    power_efficiency_curve = np.asarray(
        [[0.0, 0.83], [0.3, 0.83], [0.7, 0.90], [0.8, 0.90], [1.0, 0.85]],
        dtype=float,
    )
    capacity_power_curve = np.asarray(
        [[0.0, 1.0], [0.8, 1.0], [1.0, 0.2]], dtype=float
    )

    soc = 0.0  # CityLearn v1.3.6 StorageDevice default initial_soc.
    capacity = initial_capacity
    rows: list[dict] = []

    for row in df.itertuples(index=False):
        load = float(row.load_kwh)
        pv = float(row.pv_kwh)
        base_net = load - pv
        request = -base_net  # +charge for surplus, -discharge for deficit.

        soc_start = soc
        capacity_start = capacity
        soc_after_standby = soc_start * (1.0 - loss_coefficient)
        soc_fraction = soc_after_standby / capacity_start if capacity_start > 0 else 0.0
        max_power = nominal_power * legacy_linear_interpolation(
            soc_fraction, capacity_power_curve
        )
        if request >= 0.0:
            power_limited = min(request, max_power)
        else:
            power_limited = max(request, -max_power)

        part_load = abs(power_limited) / nominal_power if nominal_power > 0 else 0.0
        efficiency_base = legacy_linear_interpolation(
            part_load, power_efficiency_curve
        )
        efficiency = efficiency_base**efficiency_scaling

        if power_limited >= 0.0:
            soc = min(
                soc_after_standby + power_limited * efficiency,
                capacity_start,
            )
        else:
            soc = max(0.0, soc_after_standby + power_limited / efficiency)

        delta_soc_after_standby = soc - soc_after_standby
        if delta_soc_after_standby >= 0.0:
            battery_exchange = delta_soc_after_standby / efficiency
        else:
            battery_exchange = delta_soc_after_standby * efficiency

        degradation = (
            capacity_loss_coefficient
            * initial_capacity
            * abs(battery_exchange)
            / (2.0 * capacity_start)
            if capacity_start > 0
            else 0.0
        )
        capacity = capacity_start - degradation

        strategy_net = base_net + battery_exchange
        if abs(strategy_net) < 1.0e-12:
            strategy_net = 0.0
        grid_import = max(strategy_net, 0.0)
        grid_export = max(-strategy_net, 0.0)
        charge_input = max(battery_exchange, 0.0)
        discharge_output = max(-battery_exchange, 0.0)
        battery_loss = charge_input - discharge_output - (soc - soc_after_standby)

        rows.append(
            {
                "timestamp": row.timestamp,
                "month": int(row.month),
                "hour": int(row.hour),
                "day_type": row.day_type,
                "load_kwh": load,
                "pv_kwh": pv,
                "price_per_kwh": float(row.price_per_kwh),
                "carbon_intensity_kg_per_kwh": float(
                    row.carbon_intensity_kg_per_kwh
                ),
                "baseline_net_kwh": base_net,
                "control_request_kwh": request,
                "power_limited_request_kwh": power_limited,
                "battery_exchange_kwh": battery_exchange,
                "battery_charge_input_kwh": charge_input,
                "battery_discharge_output_kwh": discharge_output,
                "battery_loss_kwh": battery_loss,
                "one_way_efficiency": efficiency,
                "max_battery_power_kw": max_power,
                "soc_start_kwh": soc_start,
                "soc_end_kwh": soc,
                "capacity_start_kwh": capacity_start,
                "capacity_end_kwh": capacity,
                "capacity_degradation_kwh": degradation,
                "strategy_net_kwh": strategy_net,
                "grid_import_kwh": grid_import,
                "grid_export_kwh": grid_export,
                "hourly_cost": grid_import * float(row.price_per_kwh),
                "hourly_carbon_kg": grid_import
                * float(row.carbon_intensity_kg_per_kwh),
            }
        )

    return pd.DataFrame(rows)


def baseline_metrics(df: pd.DataFrame) -> dict[str, float]:
    net = df["load_kwh"] - df["pv_kwh"]
    imp = net.clip(lower=0.0)
    exp = (-net).clip(lower=0.0)
    direct_pv = np.minimum(df["load_kwh"], df["pv_kwh"])
    return {
        "annual_load_kwh": float(df["load_kwh"].sum()),
        "annual_pv_kwh": float(df["pv_kwh"].sum()),
        "direct_pv_use_kwh": float(direct_pv.sum()),
        "grid_import_kwh": float(imp.sum()),
        "grid_export_kwh": float(exp.sum()),
        "electricity_cost_currency": float((imp * df["price_per_kwh"]).sum()),
        "carbon_emissions_kgco2": float(
            (imp * df["carbon_intensity_kg_per_kwh"]).sum()
        ),
        "peak_grid_import_kw": float(imp.max()),
        "pv_self_consumption_fraction": float(direct_pv.sum() / df["pv_kwh"].sum()),
        "self_sufficiency_fraction": float(
            direct_pv.sum() / df["load_kwh"].sum()
        ),
    }


def strategy_metrics(hourly: pd.DataFrame, initial_capacity: float) -> dict[str, float]:
    load = float(hourly["load_kwh"].sum())
    pv = float(hourly["pv_kwh"].sum())
    imp = float(hourly["grid_import_kwh"].sum())
    exp = float(hourly["grid_export_kwh"].sum())
    charge = float(hourly["battery_charge_input_kwh"].sum())
    discharge = float(hourly["battery_discharge_output_kwh"].sum())
    ac_throughput = charge + discharge
    return {
        "annual_load_kwh": load,
        "annual_pv_kwh": pv,
        "grid_import_kwh": imp,
        "grid_export_kwh": exp,
        "electricity_cost_currency": float(hourly["hourly_cost"].sum()),
        "carbon_emissions_kgco2": float(hourly["hourly_carbon_kg"].sum()),
        "peak_grid_import_kw": float(hourly["grid_import_kwh"].max()),
        "pv_self_consumption_fraction": float(1.0 - exp / pv),
        "self_sufficiency_fraction": float(1.0 - imp / load),
        "battery_charge_input_kwh": charge,
        "battery_discharge_output_kwh": discharge,
        "battery_ac_throughput_kwh": ac_throughput,
        "equivalent_full_cycles_ac": float(ac_throughput / (2.0 * initial_capacity)),
        "battery_conversion_loss_kwh": float(hourly["battery_loss_kwh"].sum()),
        "initial_soc_kwh": float(hourly["soc_start_kwh"].iloc[0]),
        "final_soc_kwh": float(hourly["soc_end_kwh"].iloc[-1]),
        "initial_capacity_kwh": initial_capacity,
        "final_capacity_kwh": float(hourly["capacity_end_kwh"].iloc[-1]),
        "capacity_loss_kwh": float(
            initial_capacity - hourly["capacity_end_kwh"].iloc[-1]
        ),
    }


def monthly_table(hourly: pd.DataFrame) -> pd.DataFrame:
    x = hourly.copy()
    x["baseline_import_kwh"] = x["baseline_net_kwh"].clip(lower=0.0)
    x["baseline_export_kwh"] = (-x["baseline_net_kwh"]).clip(lower=0.0)
    x["baseline_cost"] = x["baseline_import_kwh"] * x["price_per_kwh"]
    x["baseline_carbon_kg"] = (
        x["baseline_import_kwh"] * x["carbon_intensity_kg_per_kwh"]
    )
    monthly = x.groupby("month", as_index=False).agg(
        load_kwh=("load_kwh", "sum"),
        pv_kwh=("pv_kwh", "sum"),
        baseline_import_kwh=("baseline_import_kwh", "sum"),
        strategy_import_kwh=("grid_import_kwh", "sum"),
        baseline_export_kwh=("baseline_export_kwh", "sum"),
        strategy_export_kwh=("grid_export_kwh", "sum"),
        baseline_cost=("baseline_cost", "sum"),
        strategy_cost=("hourly_cost", "sum"),
        baseline_carbon_kg=("baseline_carbon_kg", "sum"),
        strategy_carbon_kg=("hourly_carbon_kg", "sum"),
        baseline_peak_kw=("baseline_import_kwh", "max"),
        strategy_peak_kw=("grid_import_kwh", "max"),
        battery_charge_kwh=("battery_charge_input_kwh", "sum"),
        battery_discharge_kwh=("battery_discharge_output_kwh", "sum"),
    )
    monthly["import_reduction_kwh"] = (
        monthly["baseline_import_kwh"] - monthly["strategy_import_kwh"]
    )
    monthly["cost_saving"] = monthly["baseline_cost"] - monthly["strategy_cost"]
    monthly["carbon_reduction_kg"] = (
        monthly["baseline_carbon_kg"] - monthly["strategy_carbon_kg"]
    )
    monthly["peak_reduction_kw"] = (
        monthly["baseline_peak_kw"] - monthly["strategy_peak_kw"]
    )
    source_year_order = [8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7]
    return monthly.set_index("month").reindex(source_year_order).reset_index()


def comparison_table(base: dict, strategy: dict) -> pd.DataFrame:
    specs = [
        ("Grid import", "kWh", "grid_import_kwh", "Lower is better"),
        ("Grid export", "kWh", "grid_export_kwh", "Lower means more PV self-use"),
        ("Electricity cost", "currency", "electricity_cost_currency", "Lower is better"),
        ("Carbon emissions", "kgCO2", "carbon_emissions_kgco2", "Lower is better"),
        ("Peak grid import", "kW", "peak_grid_import_kw", "Lower is better"),
        (
            "PV self-consumption",
            "%",
            "pv_self_consumption_fraction",
            "Higher is better",
        ),
        ("Self-sufficiency", "%", "self_sufficiency_fraction", "Higher is better"),
    ]
    rows = []
    for metric, unit, key, interpretation in specs:
        b = float(base[key])
        s = float(strategy[key])
        if unit == "%":
            b *= 100.0
            s *= 100.0
            improvement = s - b
            improvement_label = "percentage-point change"
        else:
            improvement = (b - s) / b * 100.0 if b != 0 else np.nan
            improvement_label = "reduction from baseline (%)"
        rows.append(
            {
                "metric": metric,
                "unit": unit,
                "baseline": b,
                "pv_priority": s,
                "absolute_change_strategy_minus_baseline": s - b,
                "reported_improvement": improvement,
                "improvement_definition": improvement_label,
                "interpretation": interpretation,
            }
        )
    return pd.DataFrame(rows)


def run_checks(
    raw: pd.DataFrame,
    hourly: pd.DataFrame,
    base: dict,
    strategy: dict,
    battery: dict,
) -> pd.DataFrame:
    tol = 1.0e-8
    # Legacy capacity fade is applied after the SOC update. It can leave SOC a
    # few Wh above the next-step capacity and create a <=1.35e-5 kWh clamp
    # exchange. Treat this documented legacy-model artifact as numerical-scale.
    policy_tol = 2.0e-5
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append((name, bool(passed), detail))

    add("8760 hourly records", len(hourly) == 8760, f"n={len(hourly)}")
    add(
        "No missing numeric outputs",
        not hourly.select_dtypes(include=[np.number]).isna().any().any(),
        "all modeled numeric fields checked",
    )
    add(
        "SOC non-negative",
        float(hourly["soc_end_kwh"].min()) >= -tol,
        f"minimum={hourly['soc_end_kwh'].min():.12f} kWh",
    )
    add(
        "SOC within contemporaneous capacity",
        bool((hourly["soc_end_kwh"] <= hourly["capacity_start_kwh"] + tol).all()),
        f"max excess={(hourly['soc_end_kwh']-hourly['capacity_start_kwh']).max():.3e} kWh",
    )
    add(
        "Power limit respected",
        bool(
            (
                hourly["battery_exchange_kwh"].abs()
                <= hourly["max_battery_power_kw"] + tol
            ).all()
        ),
        f"max exchange={hourly['battery_exchange_kwh'].abs().max():.6f} kWh/h",
    )
    add(
        "Charging only from PV surplus",
        bool(
            (
                hourly.loc[
                    hourly["battery_charge_input_kwh"] > tol, "baseline_net_kwh"
                ]
                < tol
            ).all()
        ),
        "positive battery exchange checked against baseline net load",
    )
    add(
        "Discharging only during load deficit",
        bool(
            (
                hourly.loc[
                    hourly["battery_discharge_output_kwh"] > policy_tol,
                    "baseline_net_kwh",
                ]
                > -tol
            ).all()
        ),
        "negative battery exchange checked against baseline net load",
    )
    add(
        "No battery-induced grid export",
        bool((hourly["grid_export_kwh"] <= (-hourly["baseline_net_kwh"]).clip(lower=0.0) + policy_tol).all()),
        "strategy export does not exceed baseline beyond the 2e-5 kWh legacy capacity-clamp tolerance",
    )
    add(
        "No grid charging",
        bool(
            (
                hourly.loc[
                    hourly["battery_charge_input_kwh"] > tol, "grid_import_kwh"
                ]
                <= tol
            ).all()
        ),
        "grid import is zero in all charging hours",
    )
    balance_error = (
        hourly["strategy_net_kwh"]
        - (
            hourly["load_kwh"]
            - hourly["pv_kwh"]
            + hourly["battery_exchange_kwh"]
        )
    ).abs().max()
    add(
        "Hourly electrical balance",
        float(balance_error) <= tol,
        f"maximum absolute error={balance_error:.3e} kWh",
    )
    import_export_error = (
        hourly["strategy_net_kwh"]
        - hourly["grid_import_kwh"]
        + hourly["grid_export_kwh"]
    ).abs().max()
    add(
        "Import/export identity",
        float(import_export_error) <= tol,
        f"maximum absolute error={import_export_error:.3e} kWh",
    )
    add(
        "Capacity monotonically non-increasing",
        bool((hourly["capacity_end_kwh"].diff().dropna() <= tol).all()),
        f"start={battery['capacity']:.6f}, end={strategy['final_capacity_kwh']:.6f} kWh",
    )
    annual_balance = (
        raw["load_kwh"].sum()
        - raw["pv_kwh"].sum()
        + hourly["battery_exchange_kwh"].sum()
        - hourly["grid_import_kwh"].sum()
        + hourly["grid_export_kwh"].sum()
    )
    add(
        "Annual electrical balance",
        abs(float(annual_balance)) <= tol,
        f"residual={annual_balance:.3e} kWh",
    )
    saved_baseline = json.loads(BASELINE_SUMMARY.read_text())
    baseline_key_map = {
        "grid_import_kwh": "annual_grid_import_kwh",
        "grid_export_kwh": "annual_grid_export_kwh",
        "electricity_cost_currency": "annual_electricity_cost_currency",
        "carbon_emissions_kgco2": "annual_operational_carbon_kgco2",
        "peak_grid_import_kw": "peak_hourly_average_grid_import_kw",
    }
    add(
        "Baseline recomputation matches saved Step 6",
        all(
            abs(float(base[local_key]) - float(saved_baseline[saved_key])) <= 1.0e-8
            for local_key, saved_key in baseline_key_map.items()
        ),
        "five primary KPIs independently recomputed",
    )
    add(
        "Terminal SOC reported",
        True,
        f"initial={strategy['initial_soc_kwh']:.6f}, final={strategy['final_soc_kwh']:.6f} kWh",
    )
    return pd.DataFrame(checks, columns=["check", "passed", "detail"])


def make_figures(
    hourly: pd.DataFrame, monthly: pd.DataFrame, comparison: pd.DataFrame
) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    # Representative week: choose the week with highest PV surplus energy.
    tmp = hourly.copy()
    tmp["week"] = np.arange(len(tmp)) // 168
    tmp["surplus"] = (-tmp["baseline_net_kwh"]).clip(lower=0.0)
    week = int(tmp.groupby("week")["surplus"].sum().idxmax())
    w = tmp[tmp["week"] == week].copy()
    x = np.arange(len(w))
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(x, w["load_kwh"], label="Load", lw=1.4)
    axes[0].plot(x, w["pv_kwh"], label="PV", lw=1.4)
    axes[0].set_ylabel("Energy (kWh/h)")
    axes[0].legend(ncol=2)
    axes[0].set_title(f"PV-priority operation: representative week {week + 1}")
    axes[1].plot(x, w["baseline_net_kwh"].clip(lower=0.0), label="Baseline import")
    axes[1].plot(x, w["grid_import_kwh"], label="With battery import")
    axes[1].plot(x, -w["grid_export_kwh"], label="With battery export (negative)")
    axes[1].axhline(0, color="black", lw=0.7)
    axes[1].set_ylabel("Grid exchange (kWh/h)")
    axes[1].legend(ncol=3, fontsize=9)
    axes[2].fill_between(x, 0, w["soc_end_kwh"], alpha=0.45, label="SOC")
    axes[2].plot(x, w["capacity_end_kwh"], color="black", ls="--", label="Capacity")
    axes[2].set_ylabel("Battery energy (kWh)")
    axes[2].set_xlabel("Hour in selected week")
    axes[2].legend(ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURES / "01_representative_week.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    pairs = [
        ("baseline_import_kwh", "strategy_import_kwh", "Grid import (kWh)"),
        ("baseline_export_kwh", "strategy_export_kwh", "Grid export (kWh)"),
        ("baseline_cost", "strategy_cost", "Electricity cost (currency)"),
        ("baseline_carbon_kg", "strategy_carbon_kg", "Carbon emissions (kgCO2)"),
    ]
    month_labels = ["Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    month_x = np.arange(12)
    for ax, (b, s, title) in zip(axes.flat, pairs):
        ax.plot(month_x, monthly[b], marker="o", label="No battery")
        ax.plot(month_x, monthly[s], marker="o", label="PV priority")
        ax.set_title(title)
        ax.set_xticks(month_x, month_labels, rotation=45)
    axes[0, 0].legend()
    fig.suptitle("Monthly comparison", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGURES / "02_monthly_comparison.png", dpi=180)
    plt.close(fig)

    reduction = comparison[comparison["unit"] != "%"].copy()
    fig, ax = plt.subplots(figsize=(10, 5.3))
    bars = ax.barh(
        reduction["metric"], reduction["reported_improvement"], color="#2a9d8f"
    )
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Reduction from no-battery baseline (%)")
    ax.set_title("Annual effect of PV-priority battery control")
    for bar, val in zip(bars, reduction["reported_improvement"]):
        ax.text(val + 0.15, bar.get_y() + bar.get_height() / 2, f"{val:.2f}%", va="center")
    fig.tight_layout()
    fig.savefig(FIGURES / "03_annual_reductions.png", dpi=180)
    plt.close(fig)

    duration = pd.DataFrame(
        {
            "rank": np.arange(1, len(hourly) + 1),
            "No battery": np.sort(hourly["baseline_net_kwh"].clip(lower=0.0))[::-1],
            "PV priority": np.sort(hourly["grid_import_kwh"])[::-1],
        }
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(duration["rank"], duration["No battery"], label="No battery")
    ax.plot(duration["rank"], duration["PV priority"], label="PV priority")
    ax.set_xlabel("Hours ranked by grid import")
    ax.set_ylabel("Grid import (kW for 1-hour timestep)")
    ax.set_title("Annual grid-import load-duration curve")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "04_load_duration_curve.png", dpi=180)
    plt.close(fig)

    by_hour = hourly.groupby("hour").agg(
        mean_charge_kwh=("battery_charge_input_kwh", "mean"),
        mean_discharge_kwh=("battery_discharge_output_kwh", "mean"),
        mean_soc_kwh=("soc_end_kwh", "mean"),
    )
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax1.bar(by_hour.index - 0.18, by_hour["mean_charge_kwh"], width=0.36, label="Charge")
    ax1.bar(by_hour.index + 0.18, -by_hour["mean_discharge_kwh"], width=0.36, label="Discharge")
    ax1.axhline(0, color="black", lw=0.7)
    ax1.set_xlabel("Hour of day")
    ax1.set_ylabel("Mean battery exchange (kWh/h)")
    ax2 = ax1.twinx()
    ax2.plot(by_hour.index, by_hour["mean_soc_kwh"], color="#e76f51", marker="o", label="Mean SOC")
    ax2.set_ylabel("Mean SOC (kWh)")
    handles = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    labels = ax1.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax1.legend(handles, labels, ncol=3, loc="upper left")
    ax1.set_title("Mean diurnal battery operation")
    fig.tight_layout()
    fig.savefig(FIGURES / "05_diurnal_battery_operation.png", dpi=180)
    plt.close(fig)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(DATA_FILE).rename(
        columns={
            "time_step": "timestamp",
            "month_source": "month",
            "hour_source_1_to_24": "hour",
            "day_type_source": "day_type",
            "load_kwh_step": "load_kwh",
            "pv_generation_kwh_step": "pv_kwh",
            "electricity_price_currency_per_kwh": "price_per_kwh",
            "carbon_intensity_kgco2_per_kwh": "carbon_intensity_kg_per_kwh",
        }
    )
    schema = json.loads(SCHEMA_FILE.read_text())
    battery = schema["buildings"]["Building_5"]["electrical_storage"]["attributes"]

    hourly = run_battery_controller(raw, battery)
    base = baseline_metrics(raw)
    strategy = strategy_metrics(hourly, float(battery["capacity"]))
    monthly = monthly_table(hourly)
    comparison = comparison_table(base, strategy)
    checks = run_checks(raw, hourly, base, strategy, battery)
    if not checks["passed"].all():
        failed = checks.loc[~checks["passed"]].to_dict("records")
        raise AssertionError(f"Validation failed: {failed}")

    by_hour = hourly.groupby("hour", as_index=False).agg(
        mean_load_kwh=("load_kwh", "mean"),
        mean_pv_kwh=("pv_kwh", "mean"),
        mean_charge_kwh=("battery_charge_input_kwh", "mean"),
        mean_discharge_kwh=("battery_discharge_output_kwh", "mean"),
        mean_soc_kwh=("soc_end_kwh", "mean"),
        mean_grid_import_kwh=("grid_import_kwh", "mean"),
    )

    hourly.to_csv(RESULTS / "pv_priority_hourly.csv", index=False)
    monthly.to_csv(RESULTS / "monthly_comparison.csv", index=False)
    comparison.to_csv(RESULTS / "kpi_comparison.csv", index=False)
    by_hour.to_csv(RESULTS / "diurnal_profile.csv", index=False)
    checks.to_csv(RESULTS / "validation_checks.csv", index=False)

    summary = {
        "method": {
            "controller": "PV-priority rule-based control",
            "charge_rule": "Charge only from contemporaneous PV surplus",
            "discharge_rule": "Discharge only against contemporaneous building deficit",
            "grid_charging": False,
            "battery_export": False,
            "timestep_hours": 1.0,
            "model_reference": CITYLEARN_SOURCE,
            "model_version_emulated": "CityLearn v1.3.6",
        },
        "battery_parameters": {
            "capacity_kwh": float(battery["capacity"]),
            "nominal_power_kw": float(battery["nominal_power"]),
            "schema_efficiency": float(battery["efficiency"]),
            "loss_coefficient": float(battery["loss_coefficient"]),
            "capacity_loss_coefficient": float(
                battery["capacity_loss_coefficient"]
            ),
            "initial_soc_kwh": 0.0,
            "default_power_efficiency_curve": [
                [0.0, 0.83],
                [0.3, 0.83],
                [0.7, 0.90],
                [0.8, 0.90],
                [1.0, 0.85],
            ],
            "default_capacity_power_curve": [[0.0, 1.0], [0.8, 1.0], [1.0, 0.2]],
            "efficiency_scaling": 0.5,
        },
        "baseline": base,
        "pv_priority": strategy,
        "all_validation_checks_passed": bool(checks["passed"].all()),
    }
    (RESULTS / "pv_priority_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    make_figures(hourly, monthly, comparison)

    def val(metric: str, col: str = "pv_priority") -> float:
        return float(comparison.loc[comparison["metric"] == metric, col].iloc[0])

    findings = f"""# Step 7 — PV-priority battery control

## Scope and method

Building_5 is simulated for 8,760 hourly timesteps. The controller charges only from PV surplus and discharges only to meet the building's simultaneous deficit. Grid charging, intentional battery export, export revenue and exported-carbon credit are excluded. The battery model reproduces the relevant `StorageDevice` and `Battery` equations in CityLearn v1.3.6 using the local schema parameters: {battery['capacity']:.1f} kWh capacity, {battery['nominal_power']:.1f} kW nominal power, zero standing-loss coefficient, and capacity-loss coefficient {battery['capacity_loss_coefficient']:.0e}. CityLearn's default part-load efficiency and capacity–power curves are used because the schema does not override them.

## Annual results

| KPI | No battery | PV priority | Change |
|---|---:|---:|---:|
| Grid import (kWh) | {val('Grid import', 'baseline'):,.2f} | {val('Grid import'):,.2f} | {val('Grid import', 'reported_improvement'):.2f}% reduction |
| Grid export (kWh) | {val('Grid export', 'baseline'):,.2f} | {val('Grid export'):,.2f} | {val('Grid export', 'reported_improvement'):.2f}% reduction |
| Electricity cost (currency) | {val('Electricity cost', 'baseline'):,.2f} | {val('Electricity cost'):,.2f} | {val('Electricity cost', 'reported_improvement'):.2f}% reduction |
| Carbon emissions (kgCO2) | {val('Carbon emissions', 'baseline'):,.2f} | {val('Carbon emissions'):,.2f} | {val('Carbon emissions', 'reported_improvement'):.2f}% reduction |
| Peak grid import (kW) | {val('Peak grid import', 'baseline'):,.3f} | {val('Peak grid import'):,.3f} | {val('Peak grid import', 'reported_improvement'):.2f}% reduction |
| PV self-consumption (%) | {val('PV self-consumption', 'baseline'):.2f} | {val('PV self-consumption'):.2f} | {val('PV self-consumption', 'reported_improvement'):+.2f} percentage points |
| Self-sufficiency (%) | {val('Self-sufficiency', 'baseline'):.2f} | {val('Self-sufficiency'):.2f} | {val('Self-sufficiency', 'reported_improvement'):+.2f} percentage points |

The battery receives {strategy['battery_charge_input_kwh']:,.2f} kWh and supplies {strategy['battery_discharge_output_kwh']:,.2f} kWh on the AC side, with {strategy['battery_conversion_loss_kwh']:,.2f} kWh conversion loss. AC-side throughput is {strategy['battery_ac_throughput_kwh']:,.2f} kWh ({strategy['equivalent_full_cycles_ac']:,.1f} equivalent full cycles). Capacity declines from {strategy['initial_capacity_kwh']:.4f} to {strategy['final_capacity_kwh']:.4f} kWh under the schema degradation model. Initial and terminal SOC are {strategy['initial_soc_kwh']:.4f} and {strategy['final_soc_kwh']:.4f} kWh, respectively.

## Interpretation

This strategy directly targets PV self-consumption rather than price, carbon intensity or demand peaks. Therefore, reductions in cost, carbon and peak load are co-benefits rather than optimized outcomes. The absence of an export tariff means the reported cost is gross import cost only. Carbon is likewise assigned only to imported electricity; no credit is awarded for exports. These conventions are identical to Step 6 and make the comparison internally consistent.

## Accuracy checks

All {len(checks)} programmed checks pass: record count, missing values, SOC and power constraints, charging/discharging logic, absence of grid charging and battery-induced export, hourly and annual electrical balances, import/export identity, monotonic capacity degradation, and reproduction of the five saved Step 6 primary KPIs. See `validation_checks.csv` for numerical residuals.

## Reproducibility note

The installed environment did not contain the CityLearn Python package, so this is a transparent local reimplementation of the required legacy battery equations, not a claim that the full CityLearn environment was executed. Reference implementation: {CITYLEARN_SOURCE}.
"""
    (ROOT / "Step7_PV_Priority_Findings.md").write_text(findings, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
