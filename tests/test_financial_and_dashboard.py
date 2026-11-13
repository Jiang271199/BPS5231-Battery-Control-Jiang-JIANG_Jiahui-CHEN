"""Checks for the new financial boundary and offline dashboard data."""
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_break_even_price_has_zero_npv():
    m = runpy.run_path(str(ROOT / "30_financial_scenarios.py"))
    annual_saving, throughput, wear = 495.46, 2800.0, 0.05
    threshold = m["break_even_capex"](annual_saving, throughput, wear)
    assert threshold > 0
    assert m["npv"](annual_saving, throughput, threshold, wear) == pytest.approx(0, abs=1e-8)
    assert m["npv"](annual_saving, throughput, threshold + 1, wear) < 0


def test_dashboard_reuses_reported_full_year_schedules():
    m = runpy.run_path(str(ROOT / "31_build_dashboard.py"))
    d = m["payload"]()
    assert len(d["shared"]["load"]) == 8760
    assert len(d["series"]["S2 peak shaving"]["grid_import_kwh"]) == 8760
    assert d["kpis"]["S1 PV priority"]["electricity_cost_currency"] == pytest.approx(1045.416545, abs=1e-5)
    assert d["kpis"]["S2 peak shaving"]["peak_grid_import_kw"] == pytest.approx(4.151883, abs=1e-5)
    assert all(not name.startswith("MPC ") for name in d["rankable"])
    assert "S2 reserve 50% (what-if)" in d["series"]
    assert "S2 reserve 50% (what-if)" not in d["rankable"]
