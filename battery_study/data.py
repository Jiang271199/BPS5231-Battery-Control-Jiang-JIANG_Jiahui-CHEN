"""Input loading. Column names are normalised once here."""
from __future__ import annotations
import json
from dataclasses import dataclass
import numpy as np
import pandas as pd
from . import config

RENAME = {
    "time_step": "timestamp", "month_source": "month",
    "hour_source_1_to_24": "hour", "day_type_source": "day_type",
    "load_kwh_step": "load_kwh", "pv_generation_kwh_step": "pv_kwh",
    "electricity_price_currency_per_kwh": "price_per_kwh",
    "carbon_intensity_kgco2_per_kwh": "carbon_intensity_kg_per_kwh",
}


@dataclass(frozen=True)
class Inputs:
    df: pd.DataFrame
    battery: dict
    load: np.ndarray
    pv: np.ndarray
    net: np.ndarray
    price: np.ndarray
    carbon: np.ndarray
    hour: np.ndarray
    month: np.ndarray


def load_inputs() -> Inputs:
    df = pd.read_csv(config.DATA_FILE).rename(columns=RENAME)
    schema = json.loads(config.SCHEMA_FILE.read_text())
    battery = schema["buildings"]["Building_5"]["electrical_storage"]["attributes"]
    f = lambda c: df[c].to_numpy(dtype=float)
    return Inputs(df=df, battery=battery, load=f("load_kwh"), pv=f("pv_kwh"),
                  net=f("load_kwh") - f("pv_kwh"), price=f("price_per_kwh"),
                  carbon=f("carbon_intensity_kg_per_kwh"),
                  hour=df["hour"].to_numpy(dtype=int), month=df["month"].to_numpy(dtype=int))


def calibration_import(inp: Inputs) -> pd.Series:
    a, b = config.CALIBRATION
    return pd.Series(np.clip(inp.net[a:b], 0, None))
