#!/usr/bin/env python3
"""Fixed-controller sensitivity to battery capacity and efficiency.

No re-optimisation: selected S2 and S5 policies remain fixed. Results are
additional scenarios, not replacements for the original final KPIs.
"""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
from battery_study import battery, config, data, metrics, registry, validation

OUT = config.RESULTS / 'sensitivity' / 'capacity_efficiency_sensitivity.csv'
CAPACITIES = (4.0, 6.4, 10.0)  # kWh; baseline = 6.4
EFFICIENCIES = (0.80, 0.85, 0.90)  # reference nominal round-trip curve point = 0.90
STRATEGIES = ('S1 PV priority', 'S2 peak shaving', 'S5 min_peak', 'S5 balanced')


def run():
    inp = data.load_inputs()
    policies = registry.rule_policies(inp)
    original_curve = battery.POWER_EFF
    rows = []
    try:
        for capacity in CAPACITIES:
            for efficiency in EFFICIENCIES:
                # Keep the original part-load curve shape, scaling its round-trip
                # efficiency values relative to the original nominal 0.90 point.
                scale = efficiency / 0.90
                battery.POWER_EFF = tuple((p, min(1.0, eta * scale)) for p, eta in original_curve)
                modified = dict(inp.battery)
                modified['capacity'] = capacity
                scenario_inp = replace(inp, battery=modified)
                for name in STRATEGIES:
                    frame = battery.simulate_periodic(scenario_inp, policies[name])
                    checks = validation.validate(frame, periodic=True)
                    if not checks.passed.all():
                        raise AssertionError(f'{name}, capacity={capacity}, efficiency={efficiency}: validation failed')
                    k = metrics.kpis(frame, capacity_kwh=capacity)
                    rows.append({'strategy': name, 'battery_capacity_kwh': capacity,
                                 'nominal_roundtrip_efficiency': efficiency,
                                 'electricity_cost_currency': k['electricity_cost_currency'],
                                 'carbon_emissions_kgco2': k['carbon_emissions_kgco2'],
                                 'peak_grid_import_kw': k['peak_grid_import_kw'],
                                 'grid_import_kwh': k['grid_import_kwh'],
                                 'soc_start_kwh': k['soc_start_kwh'],
                                 'soc_end_kwh': k['soc_end_kwh']})
    finally:
        battery.POWER_EFF = original_curve
    result = pd.DataFrame(rows)
    baseline = result[(result.battery_capacity_kwh == 6.4) &
                      (result.nominal_roundtrip_efficiency == 0.90)]
    for metric in metrics.KEYS:
        base = baseline.set_index('strategy')[metric]
        result[metric + '_change_vs_base_pct'] = [
            100 * (r[metric] / base.loc[r['strategy']] - 1) for _, r in result.iterrows()
        ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    print('Saved', OUT, 'rows:', len(result))
    print(result[(result.nominal_roundtrip_efficiency == 0.90)][
        ['strategy','battery_capacity_kwh','electricity_cost_currency',
         'carbon_emissions_kgco2','peak_grid_import_kw']].to_string(index=False))


if __name__ == '__main__':
    run()
