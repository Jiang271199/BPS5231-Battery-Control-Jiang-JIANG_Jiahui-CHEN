"""Shared evaluation helpers: calibration-window scoring and full-year reporting."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from . import config, battery, metrics, validation


def score_calibration(inp, policy) -> dict:
    """Parameter selection uses ONLY the calibration window, simulated with its own
    periodic SOC boundary (no hold-out data enters the selection)."""
    a, b = config.CALIBRATION
    x = battery.simulate_periodic(inp, policy, a, b)
    k = metrics.kpis(x)
    k["periodic_residual_kwh"] = x.attrs["periodic_residual_kwh"]
    return k


def report(inp, policy, name, extra_checks=None):
    """Full-year periodic simulation; KPIs sliced by period; checks enforced."""
    x = battery.simulate_periodic(inp, policy)
    checks = validation.validate(x, periodic=True,
                                 extra=extra_checks(x) if callable(extra_checks) else extra_checks)
    if not checks.passed.all():
        raise AssertionError(f"{name}:\n" + checks.loc[~checks.passed].to_string(index=False))
    rows = [{"strategy": name, "period": p, **metrics.kpis(metrics.slice_period(x, rng))}
            for p, rng in config.PERIODS.items()]
    return x, pd.DataFrame(rows), checks


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
