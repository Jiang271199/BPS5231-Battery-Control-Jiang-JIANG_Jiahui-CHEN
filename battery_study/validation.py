"""Physical and accounting checks applied to every reported hourly result."""
from __future__ import annotations
import numpy as np
import pandas as pd

CLAMP_TOL = 2e-5  # documented legacy capacity-fade clamp (see 07_pv_priority_battery.py)


def validate(x: pd.DataFrame, periodic: bool = True, extra: dict | None = None) -> pd.DataFrame:
    checks = {
        "hourly records cover window": len(x) == int(x.timestamp.iloc[-1] - x.timestamp.iloc[0] + 1),
        "numeric outputs finite": bool(np.isfinite(x.select_dtypes(include="number").to_numpy()).all()),
        "SOC nonnegative": bool((x.soc_end_kwh >= -1e-8).all()),
        "SOC within pre-step capacity": bool((x.soc_end_kwh <= x.capacity_start_kwh + 1e-8).all()),
        "AC exchange within power limit": bool((x.battery_exchange_kwh.abs() <= x.max_battery_power_kw + 1e-8).all()),
        "hourly electrical balance": bool(np.allclose(x.strategy_net_kwh, x.load_kwh - x.pv_kwh + x.battery_exchange_kwh, atol=1e-8)),
        "grid import/export identity": bool(np.allclose(x.strategy_net_kwh, x.grid_import_kwh - x.grid_export_kwh, atol=1e-8)),
        "no simultaneous import/export": bool(((x.grid_import_kwh * x.grid_export_kwh).abs() < 1e-8).all()),
        "no intentional battery export": bool((x.grid_export_kwh <= (-x.baseline_net_kwh).clip(lower=0) + CLAMP_TOL).all()),
        "capacity nonincreasing": bool((x.capacity_end_kwh.diff().fillna(0) <= 1e-8).all()),
    }
    if periodic:
        checks["periodic SOC boundary closed (<=1e-3 kWh)"] = abs(float(x.soc_end_kwh.iloc[-1]) - float(x.soc_start_kwh.iloc[0])) <= 1e-3
    for k, v in (extra or {}).items():
        checks[k] = bool(v)
    return pd.DataFrame([{"check": k, "passed": bool(v)} for k, v in checks.items()])
