"""Prepare and audit the CityLearn 2022 Building_5 inputs for BPS5231.

Usage:
  python prepare_steps_1_to_4.py --source-dir /path/to/CityLearn_2022_Phase_All_Complete

The script never modifies the source folder. It snapshots the source files, then
builds one positionally aligned hourly table and a machine-readable audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
FILES = ["Building_5.csv", "pricing.csv", "carbon_intensity.csv", "weather.csv", "schema.json"]
BUILDING = "Building_5"
EXPECTED_STEPS = 8760


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def snapshot(source: Path, raw: Path) -> dict[str, dict[str, object]]:
    raw.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in FILES:
        src = source / name
        dst = raw / name
        if not src.is_file():
            raise FileNotFoundError(f"Required source file missing: {src}")
        source_hash = sha256(src)
        if dst.exists():
            if sha256(dst) != source_hash:
                raise RuntimeError(f"Snapshot differs from source: {dst}. Resolve before rerunning.")
        else:
            shutil.copy2(src, dst)
        manifest[name] = {"sha256": source_hash, "bytes": src.stat().st_size}
    return manifest


def audit_column(series: pd.Series) -> dict[str, object]:
    x = pd.to_numeric(series, errors="coerce")
    return {
        "rows": int(len(x)),
        "missing": int(x.isna().sum()),
        "zero_count": int((x == 0).sum()),
        "negative_count": int((x < 0).sum()),
        "min": None if x.dropna().empty else float(x.min()),
        "max": None if x.dropna().empty else float(x.max()),
        "mean": None if x.dropna().empty else float(x.mean()),
        "std": None if x.dropna().empty else float(x.std()),
        "unique": int(x.nunique(dropna=True)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_dir.expanduser().resolve()
    raw = HERE / "data" / "raw"
    processed = HERE / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    manifest = snapshot(source, raw)
    building = pd.read_csv(raw / "Building_5.csv")
    pricing = pd.read_csv(raw / "pricing.csv")
    carbon = pd.read_csv(raw / "carbon_intensity.csv")
    weather = pd.read_csv(raw / "weather.csv")
    schema = json.loads((raw / "schema.json").read_text(encoding="utf-8"))

    frames = {"building": building, "pricing": pricing, "carbon": carbon, "weather": weather}
    row_counts = {name: len(df) for name, df in frames.items()}
    if any(count != EXPECTED_STEPS for count in row_counts.values()):
        raise ValueError(f"Unexpected row counts: {row_counts}")
    if schema.get("simulation_start_time_step") != 0 or schema.get("simulation_end_time_step") != 8759:
        raise ValueError("Schema simulation window differs from 0..8759")
    if schema.get("seconds_per_time_step") != 3600:
        raise ValueError("Expected a 3600-second timestep")
    if BUILDING not in schema["buildings"]:
        raise ValueError(f"{BUILDING} not found in schema")

    cfg = schema["buildings"][BUILDING]
    expected_refs = {
        "energy_simulation": "Building_5.csv",
        "pricing": "pricing.csv",
        "carbon_intensity": "carbon_intensity.csv",
        "weather": "weather.csv",
    }
    for field, filename in expected_refs.items():
        if cfg.get(field) != filename:
            raise ValueError(f"Unexpected {field} reference: {cfg.get(field)}")

    required = {
        "building": ["month", "hour", "day_type", "daylight_savings_status", "non_shiftable_load", "solar_generation"],
        "pricing": ["electricity_pricing"],
        "carbon": ["carbon_intensity"],
        "weather": ["outdoor_dry_bulb_temperature", "outdoor_relative_humidity", "diffuse_solar_irradiance", "direct_solar_irradiance"],
    }
    for name, cols in required.items():
        missing_columns = set(cols) - set(frames[name].columns)
        if missing_columns:
            raise ValueError(f"Missing {name} columns: {sorted(missing_columns)}")
        if frames[name][cols].isna().any().any():
            raise ValueError(f"Missing values in required {name} columns")

    if not building["month"].between(1, 12).all():
        raise ValueError("Invalid month")
    if not building["hour"].between(1, 24).all():
        raise ValueError("Invalid hour")
    if not building["day_type"].between(1, 8).all():
        raise ValueError("Invalid day_type")
    if not (building["hour"].value_counts().sort_index() == 365).all():
        raise ValueError("Each hour should occur 365 times")

    pv_kw = float(cfg["pv"]["attributes"]["nominal_power"])
    battery = cfg["electrical_storage"]["attributes"]
    pv_mode = cfg["pv"]["attributes"].get("generation_mode", "per_kw")
    if pv_mode != "per_kw":
        raise ValueError(f"PV conversion requires per_kw mode, got {pv_mode}")

    # Original CityLearn per_kw convention: W/kW * installed kW / 1000,
    # yielding kWh per one-hour step.
    pv_kwh = building["solar_generation"].to_numpy(dtype=float) * pv_kw / 1000.0
    load_kwh = building["non_shiftable_load"].to_numpy(dtype=float)
    price = pricing["electricity_pricing"].to_numpy(dtype=float)
    carbon_intensity = carbon["carbon_intensity"].to_numpy(dtype=float)
    if min(load_kwh.min(), pv_kwh.min(), price.min(), carbon_intensity.min()) < 0:
        raise ValueError("Negative primary energy/price/carbon value")
    if pv_kwh.max() > pv_kw + 1e-8:
        raise ValueError("PV hourly energy exceeds installed kW times 1 hour")

    hourly = pd.DataFrame({
        "time_step": np.arange(EXPECTED_STEPS, dtype=int),
        "month_source": building["month"].astype(int),
        "hour_source_1_to_24": building["hour"].astype(int),
        "day_type_source": building["day_type"].astype(int),
        "daylight_savings_status": building["daylight_savings_status"].astype(int),
        "load_kwh_step": load_kwh,
        "pv_profile_w_per_kw": building["solar_generation"].to_numpy(dtype=float),
        "pv_generation_kwh_step": pv_kwh,
        "electricity_price_currency_per_kwh": price,
        "carbon_intensity_kgco2_per_kwh": carbon_intensity,
        "outdoor_dry_bulb_c": weather["outdoor_dry_bulb_temperature"].to_numpy(dtype=float),
        "outdoor_relative_humidity_pct": weather["outdoor_relative_humidity"].to_numpy(dtype=float),
        "diffuse_solar_irradiance_w_m2": weather["diffuse_solar_irradiance"].to_numpy(dtype=float),
        "direct_solar_irradiance_w_m2": weather["direct_solar_irradiance"].to_numpy(dtype=float),
    })
    hourly_path = processed / "building_5_hourly_inputs.csv"
    hourly.to_csv(hourly_path, index=False, float_format="%.10g")

    net = load_kwh - pv_kwh
    irradiance = hourly["diffuse_solar_irradiance_w_m2"] + hourly["direct_solar_irradiance_w_m2"]
    observed = {name: {col: audit_column(df[col]) for col in cols} for name, (df, cols) in {
        "building": (building, ["non_shiftable_load", "solar_generation", "cooling_demand", "heating_demand", "dhw_demand", "indoor_dry_bulb_temperature", "indoor_relative_humidity"]),
        "pricing": (pricing, ["electricity_pricing"]),
        "carbon": (carbon, ["carbon_intensity"]),
        "weather": (weather, ["outdoor_dry_bulb_temperature", "direct_solar_irradiance", "diffuse_solar_irradiance"]),
    }.items()}
    audit = {
        "dataset": "CityLearn Challenge 2022 Phase All",
        "building": BUILDING,
        "time_step_seconds": 3600,
        "schema_window": [0, 8759],
        "row_counts": row_counts,
        "source_files": manifest,
        "schema_parameters": {
            "pv_nominal_power_kw": pv_kw,
            "pv_generation_mode": pv_mode,
            "battery_capacity_kwh": float(battery["capacity"]),
            "battery_nominal_power_kw": float(battery["nominal_power"]),
            "battery_efficiency_parameter": float(battery["efficiency"]),
            "battery_capacity_loss_coefficient": float(battery["capacity_loss_coefficient"]),
            "battery_loss_coefficient": float(battery["loss_coefficient"]),
            "battery_depth_of_discharge_explicit": battery.get("depth_of_discharge"),
            "battery_initial_soc_explicit": battery.get("initial_soc"),
        },
        "source_calendar": {
            "first_row": building.loc[0, ["month", "hour", "day_type"]].to_dict(),
            "second_row": building.loc[1, ["month", "hour", "day_type"]].to_dict(),
            "last_row": building.loc[8759, ["month", "hour", "day_type"]].to_dict(),
            "full_timestamp_columns_present": False,
            "time_alignment_method": "same row index specified by the dataset schema; independent clock validation is impossible",
        },
        "primary_column_audit": observed,
        "derived_screening": {
            "annual_load_kwh": float(load_kwh.sum()),
            "annual_pv_kwh": float(pv_kwh.sum()),
            "pv_peak_kwh_in_one_hour": float(pv_kwh.max()),
            "load_peak_kwh_in_one_hour": float(load_kwh.max()),
            "pv_to_load_annual_ratio": float(pv_kwh.sum() / load_kwh.sum()),
            "potential_pv_surplus_hours": int((net < 0).sum()),
            "potential_grid_import_hours": int((net > 0).sum()),
            "price_carbon_pearson_r": float(np.corrcoef(price, carbon_intensity)[0, 1]),
            "pv_profile_irradiance_pearson_r": float(np.corrcoef(building["solar_generation"], irradiance)[0, 1]),
            "pv_positive_when_irradiance_zero_hours": int(((building["solar_generation"] > 1) & (irradiance < 1)).sum()),
        },
        "known_limits": [
            "The selected building is from a residential dataset, not an office dataset.",
            "Input CSVs do not contain complete timestamps; positional alignment is assumed from schema.",
            "Indoor temperature and humidity are entirely missing in this building file.",
            "Cooling/heating/DHW demand columns are zero and do not isolate end uses.",
            "CityLearn package execution and battery dynamics are not validated by this data-only audit.",
        ],
    }
    (processed / "data_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "hourly_csv": str(hourly_path),
        "rows": len(hourly),
        "annual_load_kwh": audit["derived_screening"]["annual_load_kwh"],
        "annual_pv_kwh": audit["derived_screening"]["annual_pv_kwh"],
        "price_carbon_pearson_r": audit["derived_screening"]["price_carbon_pearson_r"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
