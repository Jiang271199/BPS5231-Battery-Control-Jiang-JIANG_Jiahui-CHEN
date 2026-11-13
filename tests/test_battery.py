"""Regression and invariant tests. Run with:  python -m pytest -q"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from battery_study import battery, config, controllers as C, data, metrics, validation  # noqa: E402

INP = data.load_inputs()


def test_fast_simulator_matches_interim_s1():
    """The package simulator reproduces 07_pv_priority_battery.py's saved S1 run."""
    ref = pd.read_csv(config.ROOT / "results" / "pv_priority" / "pv_priority_hourly.csv")
    x = battery.simulate(INP, C.s1_pv_priority(INP))
    for col in ("grid_import_kwh", "grid_export_kwh", "soc_end_kwh", "capacity_end_kwh", "hourly_cost"):
        assert np.abs(x[col].to_numpy() - ref[col].to_numpy()).max() < 1e-12


def test_periodic_boundary_closes():
    cal = data.calibration_import(INP)
    pol = C.s2_peak_shaving(INP, float(cal.quantile(0.95)), 0.5, float(cal.quantile(0.6)), [15, 16, 17])
    x = battery.simulate_periodic(INP, pol)
    assert abs(x.soc_end_kwh.iloc[-1] - x.soc_start_kwh.iloc[0]) <= 1e-3
    assert validation.validate(x).passed.all()


def test_periodic_boundary_rejects_unclosed_run():
    with pytest.raises(RuntimeError, match="did not converge"):
        battery.simulate_periodic(INP, C.s1_pv_priority(INP), initial_soc=6.4,
                                  max_passes=1, tol=1e-4)


def test_energy_balance_random_policy():
    rng = np.random.default_rng(0); r = rng.uniform(-6, 6, config.N_STEPS)
    x = battery.simulate(INP, lambda t, s, c, n: r[t])
    assert np.allclose(x.strategy_net_kwh, x.load_kwh - x.pv_kwh + x.battery_exchange_kwh)
    assert (x.soc_end_kwh >= -1e-9).all() and (x.soc_end_kwh <= x.capacity_start_kwh + 1e-9).all()


def test_hypervolume_known_values():
    ref = np.array([1.0, 1.0, 1.0])
    assert abs(metrics.hypervolume_3d(np.array([[0.5, 0.5, 0.5]]), ref) - 0.125) < 1e-12
    pts = np.array([[0.0, 0.5, 0.5], [0.5, 0.0, 0.5]])
    assert abs(metrics.hypervolume_3d(pts, ref) - 0.375) < 1e-12
